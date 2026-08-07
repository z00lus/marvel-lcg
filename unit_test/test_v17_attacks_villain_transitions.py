from types import SimpleNamespace
from contextlib import ExitStack
import importlib
import unittest
from unittest.mock import Mock, patch

# Preserve the application's normal import ordering.
from engine import Engine

from game.card.face.attribute.can_attack import AttackProperty, CanAttack
from game.card.face.attribute.can_retaliate import CanRetaliate
from game.message import Message
from game.message.message_type import CanBeInstead
from game.player.scenario import Scenario


class V17AttackAndVillainTransitionTests(unittest.TestCase):

    def _run_attack_with_stage_transition(self, *, same_title: bool):
        player = SimpleNamespace(IsPlayer=lambda: True)
        world = SimpleNamespace(
            is_game_over=False,
            stat=SimpleNamespace(RecordAttack=Mock()),
        )
        scenario = SimpleNamespace(world=world)
        effect = SimpleNamespace(
            world=world,
            ability=SimpleNamespace(IsLabel=lambda _label: False),
        )

        shared_card = Mock()
        shared_card.world = world
        shared_card.on_field = True
        shared_card.state = SimpleNamespace(is_advancing=False)
        previous_printed_face = SimpleNamespace(paper=object())
        shared_card.printed_faces = [previous_printed_face]

        previous = Mock()
        previous.name = 'Stage Villain'
        previous.card = shared_card
        previous.attack = 1
        previous.victory = False
        previous.encounter_deck = object()
        previous.IsInPlay.side_effect = lambda: shared_card.on_field
        previous.IsDefeated.return_value = False
        previous.IsPlayer.return_value = False
        previous.GetControlByOrOwner.return_value = player
        previous.CastTo.return_value = previous
        previous.GetBoostCardNum.return_value = 1
        shared_card.face = previous
        shared_card.CastTo.side_effect = lambda _type: shared_card.face

        target = Mock()
        target.card.CastTo.return_value = target
        target.GetControlByOrOwner.return_value = player
        target.IsDefeated.return_value = False
        target.IsInPlay.return_value = True
        target.IsTough.return_value = False
        target.ResolveRetaliate.return_value = None
        damage_result = SimpleNamespace(
            took_damage=5,
            excess_damage=0,
            who_took_damage=target,
            damaged_overkill_target=None,
        )
        target.TakeDamageWithOverkillTarget.return_value = [damage_result]

        next_villain = Mock()
        next_villain.victory = False
        next_villain.IsName.return_value = same_title
        next_villain.card.area.flags.is_victory_display = False

        created_faces = []
        if same_title:
            next_printed_face = SimpleNamespace(
                paper=object(),
                IsName=lambda _name: True,
            )
            next_villain.card.printed_faces = [next_printed_face]
            new_stage = Mock()
            new_stage.name = previous.name
            new_stage.card = shared_card
            new_stage.attack = 5
            new_stage.IsInPlay.return_value = True
            new_stage.IsDefeated.return_value = False
            new_stage.IsPlayer.return_value = False
            new_stage.GetControlByOrOwner.return_value = player
            new_stage.CastTo.return_value = new_stage

            def set_same_stage(face, _backs, _remove_legacy):
                shared_card.face = face
                face.card = shared_card
                return face

            shared_card.SetAsCard.side_effect = set_same_stage
            created_faces = [object(), new_stage]
        else:
            new_stage = next_villain
            next_villain.card.printed_faces = []

        def remove_old_stage(faces, _effect):
            if previous in faces:
                shared_card.on_field = False

        def resolve_boost(_being_message, _gain):
            Scenario.AdvanceVillainStage(
                scenario,
                previous,
                effect,
                to_villain=next_villain,
            )

        previous.ResolveBoostCards.side_effect = resolve_boost

        would_attack = SimpleNamespace(
            is_be_instead=False,
            attacked_targets=[target],
            gain_atk=0,
            defender=None,
            property=AttackProperty(is_basic_power=True, against_player=player),
            Send=Mock(),
            IsBasicAttack=lambda: True,
        )
        being_attacked = SimpleNamespace(
            defender=None,
            defense_messages=[],
            gain_atk=0,
            Send=Mock(),
        )

        def would_attack_unit(_attacker, attacked, _being):
            return SimpleNamespace(
                target=attacked,
                gain_atk=0,
                temp_additional_value=0,
                Send=Mock(),
                HasKeywords=lambda: False,
                IsPiercing=lambda: False,
                IsOverKill=lambda: False,
                ChangeTarget=Mock(),
            )

        def calculated(_attacker, _target, damage, defense, _boosts, _would):
            return SimpleNamespace(
                calculated_damage=max(0, damage - defense),
                Send=Mock(),
            )

        attack_end = Mock()
        attack_end.Send = Mock()

        patchers = [
            patch('game.card.face.base.Unit2.IsType', return_value=True),
            patch('game.card.face.base.Enemy.IsType', return_value=True),
            patch('game.card.face.attribute.can_boost.CanBoost.IsType', return_value=True),
            patch('game.card.face.attribute.can_attack.CanAttack.IsType', return_value=True),
            patch('game.card.face.attribute.can_attack.HasAttack.IsType', return_value=True),
            patch('game.card.face.card_type.Minion.IsType', return_value=False),
            patch('game.card.face.card_type.Ally.IsType', return_value=False),
            patch('game.message.Message.WhenUnitWouldAttack', return_value=would_attack),
            patch('game.message.Message.WhenEnemyActivateAgainstYou', return_value=Mock()),
            patch('game.message.Message.WhenUnitUseBasicPower', return_value=Mock()),
            patch('game.message.Message.WhenUnitBeingAttack', return_value=being_attacked),
            patch('game.message.Message.WhenUnitWouldAttackUnit', side_effect=would_attack_unit),
            patch('game.message.Message.CheckIfAttackMessageHasKeyword', return_value=Mock()),
            patch('game.message.Message.WhenCalculateAttackDamage', side_effect=calculated),
            patch('game.message.Message.AfterUnitAttackUnit', return_value=Mock()),
            patch('game.message.Message.AttackEndsBeforeDamageDealt', return_value=Mock()),
            patch('game.message.Message.AfterUnitAttackEnd', return_value=attack_end),
            patch('game.message.Message.AfterEnemyActivationEnd', return_value=Mock()),
            patch('game.message.Message.AfterUnitUseBasicPower', return_value=Mock()),
            patch('game.message.Message.WhenVillainWouldAdvance', return_value=Mock()),
            patch('game.message.Message.WhenVillainAdvance', return_value=Mock()),
            patch('game.message.Message.AfterVillainAdvanced', return_value=Mock()),
            patch('game.effect.rule.GameRule', return_value=effect),
            patch('game.card.factory.CardFactory.CreateFace', side_effect=created_faces),
            patch('game.card.factory.CardFactory.CardRegisterEffects'),
            patch('game.operate.faces.Faces.RemoveAllFromGame', side_effect=remove_old_stage),
            patch('game.operate.effects.Effects.UnRegister'),
        ]
        with ExitStack() as stack:
            for patcher in patchers:
                stack.enter_context(patcher)
            result = CanAttack.AttackInternal(
                previous,
                [target],
                effect,
                property=would_attack.property,
            )

        return result, target, shared_card, new_stage

    def test_direct_ally_attack_and_cross_player_defender_retarget_the_attacked_player(self):
        first_player = object()
        defending_player = object()
        direct_ally = SimpleNamespace(GetControlByOrOwner=lambda: first_player)
        cross_player_defender = SimpleNamespace(GetControlByOrOwner=lambda: defending_player)
        property = AttackProperty()

        with patch('game.player.Player.IsType', return_value=True):
            attacked = CanAttack.RetargetAttackedPlayer(direct_ally, property)
            defended = CanAttack.RetargetAttackedPlayer(cross_player_defender, property)

        self.assertIs(attacked, first_player)
        self.assertIs(defended, defending_player)
        self.assertIs(property.against_player, defending_player)

    def test_ally_defender_that_leaves_play_retargets_its_controllers_identity(self):
        identity = object()
        controller = SimpleNamespace(GetIdentity=lambda: identity)
        original_target = object()
        defender = SimpleNamespace(GetControlByOrOwner=lambda: controller)

        with patch('game.card.face.card_type.Ally.IsType', return_value=True), \
            patch('game.player.Player.IsType', return_value=True):
            target = CanAttack.GetUndefendedTarget(original_target, defender)

        self.assertIs(target, identity)

    def test_zero_damage_piercing_does_not_discard_tough(self):
        attack = SimpleNamespace(IsPiercing=lambda: True)
        target = SimpleNamespace(IsTough=lambda: True)

        self.assertFalse(CanAttack.ShouldDiscardToughForPiercing(0, attack, target))
        self.assertTrue(CanAttack.ShouldDiscardToughForPiercing(1, attack, target))

    def test_retaliate_requires_both_characters_to_remain_in_play(self):
        attacker = SimpleNamespace(
            IsInPlay=lambda: True,
            IsDefeated=lambda: False,
            TakeDamage=Mock(),
        )
        attack = SimpleNamespace(
            attacker=attacker,
            IsRanged=lambda: False,
            IsIgnoreRetaliate=lambda: False,
        )
        defender = SimpleNamespace(
            retaliate=1,
            IsInPlay=lambda: False,
            IsDefeated=lambda: False,
        )

        self.assertIsNone(CanRetaliate.ResolveRetaliate(defender, attack))
        attacker.TakeDamage.assert_not_called()

    def test_same_title_stage_can_continue_but_removed_different_title_stage_cannot(self):
        same_title_stage = SimpleNamespace(IsInPlay=lambda: True)
        removed_old_stage = SimpleNamespace(IsInPlay=lambda: False)

        self.assertTrue(CanAttack.CanContinueInterruptedActivation(same_title_stage))
        self.assertFalse(CanAttack.CanContinueInterruptedActivation(removed_old_stage))

    def test_different_title_villain_stage_enters_as_a_new_character(self):
        world = SimpleNamespace(is_game_over=False)
        scenario = SimpleNamespace(world=world)
        effect = SimpleNamespace(world=world)
        previous = Mock()
        previous.name = 'Old Villain'
        previous.victory = False
        previous.card.area.flags.is_victory_display = False
        next_villain = Mock()
        next_villain.IsName.return_value = False
        next_villain.victory = False
        next_villain.card.area.flags.is_victory_display = False

        with patch('game.message.Message.WhenVillainWouldAdvance') as would_advance, \
            patch('game.message.Message.WhenVillainAdvance') as advance, \
            patch('game.message.Message.AfterVillainAdvanced') as after, \
            patch('game.effect.rule.GameRule', return_value=object()), \
            patch('game.operate.faces.Faces.RemoveAllFromGame') as remove:
            result = Scenario.AdvanceVillainStage(
                scenario,
                previous,
                effect,
                to_villain=next_villain,
            )

        self.assertFalse(result)
        next_villain.PutIntoPlay.assert_called_once_with('FirstPlayer', effect)
        remove.assert_called_once()
        would_advance.assert_called_once_with(previous)
        advance.assert_called_once_with(next_villain, effect)
        after.assert_called_once()

    def test_same_title_villain_stage_reuses_card_and_emits_one_would_advance(self):
        world = SimpleNamespace(is_game_over=False)
        scenario = SimpleNamespace(world=world)
        effect = SimpleNamespace(world=world)

        previous_face = SimpleNamespace(paper=object())
        next_face = SimpleNamespace(paper=object(), IsName=lambda _name: True)
        shared_card = Mock()
        shared_card.printed_faces = [previous_face]
        shared_card.state = SimpleNamespace(is_advancing=False)
        shared_card.continuity_marker = object()
        previous = Mock()
        previous.name = 'Continuing Villain'
        previous.card = shared_card
        previous.encounter_deck = object()

        next_card = Mock()
        next_card.printed_faces = [next_face]
        next_card.area.flags.is_victory_display = False
        next_villain = Mock()
        next_villain.card = next_card
        next_villain.victory = False
        next_villain.IsName.return_value = True

        old_created = object()
        new_created = Mock()
        new_villain = Mock()
        new_villain.card = shared_card
        new_villain.CastTo.return_value = new_villain
        shared_card.SetAsCard.return_value = new_villain

        with patch('game.message.Message.WhenVillainWouldAdvance') as would_advance, \
            patch('game.message.Message.WhenVillainAdvance') as advance, \
            patch('game.message.Message.AfterVillainAdvanced') as after, \
            patch('game.effect.rule.GameRule', return_value=object()), \
            patch('game.card.factory.CardFactory.CreateFace', side_effect=[old_created, new_created]), \
            patch('game.card.factory.CardFactory.CardRegisterEffects'), \
            patch('game.operate.faces.Faces.RemoveAllFromGame'):
            result = Scenario.AdvanceVillainStage(
                scenario,
                previous,
                effect,
                to_villain=next_villain,
            )

        self.assertFalse(result)
        next_villain.PutIntoPlay.assert_not_called()
        next_card.SetAsCard.assert_called_once_with(old_created, [], True)
        shared_card.SetAsCard.assert_called_once_with(new_created, [], True)
        new_villain.SetEncounterDeck.assert_called_once_with(previous.encounter_deck)
        new_villain.ResetHealth.assert_called_once()
        self.assertIsNotNone(shared_card.continuity_marker)
        would_advance.assert_called_once_with(previous)
        advance.assert_called_once_with(new_villain, effect)
        after.assert_called_once()

    def test_same_title_stage_transition_during_activation_resumes_with_new_attack(self):
        result, target, shared_card, new_stage = self._run_attack_with_stage_transition(
            same_title=True,
        )

        self.assertIs(shared_card.face, new_stage)
        self.assertIsNotNone(result)
        target.TakeDamageWithOverkillTarget.assert_called_once()
        self.assertEqual(target.TakeDamageWithOverkillTarget.call_args.args[1], 5)

    def test_different_title_stage_transition_during_activation_ends_before_damage(self):
        result, target, shared_card, _new_stage = self._run_attack_with_stage_transition(
            same_title=False,
        )

        self.assertFalse(shared_card.on_field)
        self.assertIsNotNone(result)
        target.TakeDamageWithOverkillTarget.assert_not_called()

    def test_revealing_a_villain_cannot_be_replaced_or_canceled(self):
        message = object.__new__(Message.WhenCardWouldReveal)
        message.private_trigger = object()
        effect = object()

        with patch('game.card.face.base.Villain.IsType', return_value=True), \
            patch.object(CanBeInstead, 'SetBeInstead') as replace:
            Message.WhenCardWouldReveal.SetBeInstead(message, effect)

        replace.assert_not_called()

    def test_villain_and_main_scheme_when_revealed_effects_cannot_be_canceled(self):
        reveal = SimpleNamespace(
            cannot_be_cancel=True,
            cancel_when_revealed=False,
            cancel_all_effects=False,
        )

        Message.WhenPlayerRevealCard.CancelWhenRevealedEffect(reveal, object())
        Message.WhenPlayerRevealCard.CancelAllEffectsInternal(reveal, object())

        self.assertFalse(reveal.cancel_when_revealed)
        self.assertFalse(reveal.cancel_all_effects)

    def test_villain_named_boost_effect_still_targets_villain_for_villainous_minion(self):
        module = importlib.import_module('cards.pack.mut_gen.master_mold.32118')
        boost_ability = module.GetAbilities()[1]
        villain = object()
        effect = SimpleNamespace(
            this=SimpleNamespace(CastTo=lambda _type: object()),
        )
        message = SimpleNamespace(attacker=object())

        with patch.object(module.Worlds, 'FindVillain', return_value=villain), \
            patch.object(module.Faces, 'GiveStatus') as give_status:
            boost_ability.operation(effect, message)

        give_status.assert_called_once_with([villain], 'Tough', effect)


if __name__ == '__main__':
    unittest.main()
