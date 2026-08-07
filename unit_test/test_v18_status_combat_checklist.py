from types import SimpleNamespace
import importlib
import unittest
from unittest.mock import Mock, patch

# Preserve the application's normal import ordering.
from engine import Engine

from game.ability.ability_type import TimingPriority
from game.card.face.attribute.can_attack import AttackProperty, CanAttack
from game.card.face.attribute.can_quickstrike import CanQuickstrike
from game.card.face.attribute.can_retaliate import CanRetaliate
from game.card.face.attribute.can_status import CanStatus
from game.card.face.model.face_action import ModelAction
from game.event.manager import EventManager
from game.message import Message
from game.message.message_type import CanBeInstead
from game.player.action.player_action import PlayerAction
from game.selector.selector_rule import SelectorRule
from game.selector.selector_range import SelectorRange


class _StatusComponent:

    def __init__(self, counts=None):
        self.counts = {
            'Confused': 0,
            'Stunned': 0,
            'Tough': 0,
        }
        if counts:
            self.counts.update(counts)

    @property
    def confused(self):
        return self.counts['Confused']

    @property
    def stunned(self):
        return self.counts['Stunned']

    @property
    def tough(self):
        return self.counts['Tough']

    def GiveStatusCard(self, name, by_effect):
        self.counts[name] += 1
        return SimpleNamespace(name=name)

    def DiscardStatusCard(self, name, by_effect, rule):
        if rule == 'All':
            discard = self.counts[name]
        elif rule == 'Steady' and name in ('Stunned', 'Confused'):
            discard = 2 if self.parent.IsSteady() else 1
        else:
            discard = min(int(rule), self.counts[name])
        self.counts[name] -= discard
        return discard


class _StatusUnit:

    def __init__(self, *, steady=False, stalwart=False, counts=None):
        status = _StatusComponent(counts)
        status.parent = self
        self.components = SimpleNamespace(status=status)
        self.card = SimpleNamespace(
            IsOnField=lambda: True,
            CastTo=lambda card_type: self,
        )
        self._steady = steady
        self._stalwart = stalwart
        self.tough_max = 1

    @property
    def confused(self):
        return self.components.status.confused

    @property
    def stunned(self):
        return self.components.status.stunned

    @property
    def tough(self):
        return self.components.status.tough

    def IsInPlay(self):
        return True

    def IsSteady(self):
        return self._steady

    def IsStalwart(self):
        return self._stalwart

    def GetBuff(self, buff):
        return False

    def IsConfused(self):
        return CanStatus.IsConfused(self)

    def IsStunned(self):
        return CanStatus.IsStunned(self)

    def IsTough(self):
        return CanStatus.IsTough(self)

    def CanbeConfused(self):
        return CanStatus.CanbeConfused(self)

    def CanbeStunned(self):
        return CanStatus.CanbeStunned(self)

    def GainStatus(self, name, by_effect):
        return CanStatus.GainStatus(self, name, by_effect)

    def LoseState(self, name, by_effect, rule):
        return CanStatus.LoseState(self, name, by_effect, rule)

    def DiscardConfused(self, by_effect, *, rule):
        return CanStatus.DiscardConfused(self, by_effect, rule=rule)

    def DiscardStunned(self, by_effect, *, rule):
        return CanStatus.DiscardStunned(self, by_effect, rule=rule)

    def DiscardTough(self, by_effect, *, rule):
        return CanStatus.DiscardTough(self, by_effect, rule=rule)


class V18StatusChecklistTests(unittest.TestCase):

    def SetUpStatusMessages(self):
        would_place = Mock(is_be_instead=False)
        placed = Mock()
        return would_place, placed

    def Gain(self, unit, name):
        would_place, placed = self.SetUpStatusMessages()
        with patch.object(
            Message,
            'WhenStatusWouldCardPlaceOn',
            return_value=would_place,
        ), patch.object(
            Message,
            'AfterStatusCardPlaceOn',
            return_value=placed,
        ):
            result = unit.GainStatus(name, object())
        return result, would_place, placed

    def ResolveStatus(self, module_name, ability_index, unit):
        ability = importlib.import_module(module_name).GetAbilities()[ability_index]
        status = Mock()
        status.GetBindFace.return_value = unit
        source = Mock()
        source.CastTo.return_value = status
        effect = SimpleNamespace(this=source)
        message = Mock()

        ability.operation(effect, message)
        return message, effect

    def test_stunned_replaces_next_attack_and_discards_the_status(self):
        unit = _StatusUnit(counts={'Stunned': 1})

        message, effect = self.ResolveStatus(
            'cards.pack.status.stunned',
            0,
            unit,
        )

        message.SetBeInstead.assert_called_once_with(effect)
        self.assertEqual(unit.stunned, 0)
        self.assertFalse(unit.IsStunned())

    def test_confused_replaces_next_thwart_and_discards_the_status(self):
        unit = _StatusUnit(counts={'Confused': 1})

        message, effect = self.ResolveStatus(
            'cards.pack.status.confused',
            1,
            unit,
        )

        message.SetBeInstead.assert_called_once_with(effect)
        self.assertEqual(unit.confused, 0)
        self.assertFalse(unit.IsConfused())

    def test_tough_prevents_an_entire_large_damage_instance_and_discards(self):
        unit = _StatusUnit(counts={'Tough': 1})
        damage_message = Mock()
        damage_message.property.damage = 99
        ability = importlib.import_module(
            'cards.pack.status.tough'
        ).GetAbilities()[0]
        status = Mock()
        status.GetBindFace.return_value = unit
        source = Mock()
        source.CastTo.return_value = status
        effect = SimpleNamespace(this=source)

        ability.operation(effect, damage_message)

        damage_message.SetBeInstead.assert_called_once_with(effect)
        self.assertEqual(unit.tough, 0)

    def test_steady_requires_two_status_cards_and_discards_both_on_use(self):
        unit = _StatusUnit(steady=True)

        first, _, _ = self.Gain(unit, 'Stunned')
        self.assertTrue(first)
        self.assertEqual(unit.stunned, 1)
        self.assertFalse(unit.IsStunned())

        second, _, _ = self.Gain(unit, 'Stunned')
        self.assertTrue(second)
        self.assertEqual(unit.stunned, 2)
        self.assertTrue(unit.IsStunned())

        self.ResolveStatus('cards.pack.status.stunned', 0, unit)
        self.assertEqual(unit.stunned, 0)

    def test_stalwart_rejects_stunned_and_confused(self):
        unit = _StatusUnit(stalwart=True)

        for name in ('Stunned', 'Confused'):
            with self.subTest(status=name):
                result, would_place, placed = self.Gain(unit, name)
                self.assertFalse(result)
                would_place.Send.assert_not_called()
                placed.Send.assert_not_called()

        self.assertEqual(unit.stunned, 0)
        self.assertEqual(unit.confused, 0)

    def test_repeated_status_does_not_create_invalid_extra_copies(self):
        normal = _StatusUnit()
        steady = _StatusUnit(steady=True)

        for unit, expected_max in ((normal, 1), (steady, 2)):
            for _ in range(4):
                self.Gain(unit, 'Confused')
            with self.subTest(steady=unit.IsSteady()):
                self.assertEqual(unit.confused, expected_max)

        tough = _StatusUnit()
        for _ in range(4):
            self.Gain(tough, 'Tough')
        self.assertEqual(tough.tough, 1)


class V18CombatChecklistTests(unittest.TestCase):

    def MakeCalculateDamage(self, attack, defense):
        world = SimpleNamespace(
            is_game_over=False,
            object_manager=SimpleNamespace(AddObject=lambda category, obj: 1),
        )
        attacker = Mock()
        attacker.card.world = world
        attacker.CastTo.return_value = attacker
        target = Mock()
        target.card.world = world
        broad_attack = SimpleNamespace(defender=None)
        attack_unit = SimpleNamespace(would_atk_message=broad_attack)
        return Message.WhenCalculateAttackDamage(
            attacker,
            target,
            attack,
            defense,
            [],
            attack_unit,
        )

    def test_basic_attack_uses_current_value_with_all_persistent_modifiers(self):
        hero = SimpleNamespace(attack=5)
        attack = AttackProperty(is_basic_power=True, additional_value=2)

        with patch(
            'game.card.face.attribute.can_attack.HasAttack.IsType',
            return_value=True,
        ):
            self.assertEqual(attack.GetDamage(hero), 7)

    def test_temporary_attack_bonus_is_removed_at_the_attack_end_window(self):
        registered = []
        gain_calls = []
        face = Mock()
        face.paper.card_id = 'test'
        face.card.face = face
        face.IsInPlay.return_value = True

        def gain(by_effect, diff, **kwargs):
            if kwargs.get('attack') is not None:
                gain_calls.append((diff, kwargs['attack']))
                return True
            return False

        def registers(ability):
            registered.append(ability)
            return [SimpleNamespace(ability=ability)]

        face.Gain.side_effect = gain
        face.effect.Registers.side_effect = registers
        model = SimpleNamespace(GetThis=lambda: face)
        active_attack = object.__new__(Message.WhenUnitWouldAttack)
        active_attack.AddGainedATK = Mock()
        by_effect = object()

        with patch(
            'game.card.face.card_type.Ally.IsType',
            return_value=False,
        ), patch(
            'game.message.Message.AfterCardApply_Text',
        ), patch(
            'game.operate.effects.Effects.UnRegister',
        ):
            ModelAction.TemporaryGain(
                model,
                by_effect,
                active_attack,
                attack=3,
            )
            cleanup = next(
                ability for ability in registered
                if ability.when is Message.AfterUnitAttackEnd
            )
            end_message = SimpleNamespace(would_atk_messages=[active_attack])
            self.assertTrue(cleanup.conditions[0](Mock(), end_message))
            cleanup.operation(Mock(), end_message)

        active_attack.AddGainedATK.assert_called_once_with(3)
        self.assertEqual(gain_calls, [(1, 3), (-1, 3)])

    def test_hero_defense_reduces_attack_damage_once_and_not_below_zero(self):
        self.assertEqual(self.MakeCalculateDamage(8, 3).calculated_damage, 5)
        self.assertEqual(self.MakeCalculateDamage(2, 5).calculated_damage, 0)

    def test_ally_defender_retargets_damage_to_the_ally_controller(self):
        player = object()
        ally = SimpleNamespace(GetControlByOrOwner=lambda: player)
        attack = AttackProperty()

        with patch('game.player.Player.IsType', return_value=True):
            result = CanAttack.RetargetAttackedPlayer(ally, attack)

        self.assertIs(result, player)
        self.assertIs(attack.against_player, player)

    def test_indirect_damage_can_be_split_between_legal_characters(self):
        identity = Mock()
        ally = Mock()
        identity.TakeDamage.return_value = object()
        ally.TakeDamage.return_value = object()
        player = Mock()
        player.ChooseAbilities.return_value = [
            SimpleNamespace(targets=[identity, ally, identity]),
        ]
        action = SimpleNamespace(GetPlayer=lambda: player)

        PlayerAction.AssignDamage(
            action,
            [identity, ally],
            object(),
            3,
            object(),
        )

        self.assertEqual(identity.TakeDamage.call_args.args[1].damage, 2)
        self.assertEqual(ally.TakeDamage.call_args.args[1].damage, 1)
        self.assertTrue(identity.TakeDamage.call_args.args[1].is_indirect_damage)

    def test_indirect_damage_selector_caps_each_character_at_current_hp(self):
        identity = Mock(health=2)
        ally = Mock(health=1)
        rule = SelectorRule(repeat_rules=['Health'])
        selector_range = SelectorRange((0, 10), rule)

        with patch(
            'game.card.face.base.Unit2.IsType',
            return_value=True,
        ):
            choices = rule.Process(
                [identity, ally],
                SimpleNamespace(),
                selector_range,
            )

        self.assertEqual(choices.count(identity), 2)
        self.assertEqual(choices.count(ally), 1)

    def test_tough_replacement_precedes_damage_reduction_interrupts(self):
        class DamageWindow(CanBeInstead):
            pass

        world = SimpleNamespace(
            is_game_over=False,
            is_initializing=False,
            object_manager=SimpleNamespace(AddObject=lambda category, obj: 1),
        )
        manager = EventManager(world)
        message = DamageWindow(world=world)

        def make_effect(name, priority, forced):
            return SimpleNamespace(
                name=name,
                is_unregister=False,
                is_local=False,
                is_nonkeyword=False,
                is_rule=False,
                is_forced=forced,
                priority=priority,
                ability=SimpleNamespace(
                    when=DamageWindow,
                    flags=SimpleNamespace(
                        is_statistics=False,
                        is_temp=False,
                    ),
                ),
            )

        tough = make_effect('Tough', TimingPriority.Status, True)
        reduction = make_effect(
            'Damage reduction',
            TimingPriority.Interrupt,
            False,
        )
        manager.RegisterEffect(reduction)
        manager.RegisterEffect(tough)

        def resolve_tough(message, effects, priority, undo):
            message.be_instead_internal = True
            return True

        with patch.object(
            manager,
            'ProcessForcedEffect',
            side_effect=resolve_tough,
        ) as process_tough, patch.object(
            manager,
            'ProcessOptionalEffect',
        ) as process_reduction:
            manager.BroadcastMessage(message)

        process_tough.assert_called_once_with(
            message,
            [tough],
            TimingPriority.Status,
            None,
        )
        process_reduction.assert_not_called()
        self.assertTrue(message.is_be_instead)

    def test_retaliate_requires_a_completed_survived_non_ranged_attack(self):
        attacker = SimpleNamespace(
            IsInPlay=lambda: True,
            IsDefeated=lambda: False,
            TakeDamage=Mock(return_value='retaliated'),
        )
        defender = SimpleNamespace(
            retaliate=2,
            IsInPlay=lambda: True,
            IsDefeated=lambda: False,
        )

        for ranged, defender_defeated, expected in (
            (False, False, True),
            (True, False, False),
            (False, True, False),
        ):
            with self.subTest(ranged=ranged, defeated=defender_defeated):
                defender.IsDefeated = lambda value=defender_defeated: value
                attack = SimpleNamespace(
                    attacker=attacker,
                    IsRanged=lambda value=ranged: value,
                    IsIgnoreRetaliate=lambda: False,
                )
                self.assertEqual(
                    CanRetaliate.CanResolveRetaliate(defender, attack),
                    expected,
                )

        valid_attack = SimpleNamespace(
            attacker=attacker,
            IsRanged=lambda: False,
            IsIgnoreRetaliate=lambda: False,
        )
        defender.IsDefeated = lambda: False
        with patch('game.effect.rule.Retaliate', return_value='effect'):
            result = CanRetaliate.ResolveRetaliate(defender, valid_attack)
        self.assertEqual(result, 'retaliated')
        attacker.TakeDamage.assert_called_once_with(defender, 2, 'effect')

    def test_quickstrike_attacks_after_engaging_a_hero(self):
        player = SimpleNamespace(
            IsHero=lambda: True,
            GetIdentity=lambda: object(),
        )
        minion = SimpleNamespace(
            IsInPlay=lambda: True,
            IsQuickstrike=lambda: True,
            DoAttackYou=Mock(),
        )

        with patch(
            'game.card.face.base.Enemy.IsType',
            return_value=True,
        ), patch('game.effect.rule.Quickstrike', return_value='quickstrike'):
            CanQuickstrike.ResolveQuickstrike(minion, player)

        minion.DoAttackYou.assert_called_once_with(player, 'quickstrike')

    def test_quickstrike_does_not_attack_without_a_valid_hero_target(self):
        minion = SimpleNamespace(
            IsInPlay=lambda: True,
            IsQuickstrike=lambda: True,
            DoAttackYou=Mock(),
        )
        alter_ego_player = SimpleNamespace(IsHero=lambda: False)

        with patch(
            'game.card.face.base.Enemy.IsType',
            return_value=True,
        ):
            CanQuickstrike.ResolveQuickstrike(minion, alter_ego_player)

        minion.DoAttackYou.assert_not_called()


if __name__ == '__main__':
    unittest.main()
