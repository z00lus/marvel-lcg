from types import SimpleNamespace
import importlib
import unittest
from unittest.mock import Mock, patch

# Preserve the application's normal import ordering for card scripts.
from engine import Engine

from cards.paper import Paper
from game.ability.cost_func import CostFunc
from game.ability.factory.treat import TreatAsMinion
from game.card.face.attribute.can_attach import CanAttach
from game.card.face.attribute.can_health import CanHealth
from game.card.face.attribute.can_status import CanStatus
from game.card.face.attribute.has_attribute import HasAttribute
from game.card.face.base.scheme import Scheme2
from game.card.face.card_face import CardFace
from game.card.face.component.counter import Counter
from game.card.face.component.token import Token
from game.card.face.model.face_gain import ModelGain
from game.operate.faces import Faces
from game.operate.search import Search
from game.operate.worlds import Worlds
from game.player.element.player_phase import PlayerPhase


class _CounterCard:
    def __init__(self, counter: '_Counter') -> None:
        self.counter = counter

    def CastTo(self, _type):
        return self.counter


class _Counter:
    def __init__(self, counter_name: str, count: int) -> None:
        self.counter_name = counter_name
        self.count = count
        self.card = _CounterCard(self)
        self.removals = []
        self.placements = []

    def RemoveCountersInternal(self, value, name, by_effect, *, forced):
        self.removals.append((value, name, forced, by_effect))
        if name == 'all-purpose':
            name = self.counter_name
        removed = min(value, self.count)
        self.count -= removed
        return SimpleNamespace(removed_counters=removed, counter_name=name)

    def PlaceCountersInternal(self, value, name, by_effect):
        self.placements.append((value, name, by_effect))
        if name == 'all-purpose':
            name = self.counter_name
        self.count += value
        self.placed_as = name
        return value


class _Deck:
    def __init__(self, *faces) -> None:
        self.faces = list(faces)

    def GetAll(self):
        return list(self.faces)


class V17CounterAndCardStateTests(unittest.TestCase):

    def test_all_purpose_counter_takes_the_destination_type_when_moved(self):
        source = _Counter('charge', 2)
        destination = _Counter('ammo', 0)
        effect = object()

        moved = Faces.MoveCounters(source, destination, 1, 'all-purpose', effect)

        self.assertEqual(moved, 1)
        self.assertEqual(source.count, 1)
        self.assertEqual(destination.count, 1)
        self.assertEqual(source.removals[0][1], 'all-purpose')
        self.assertEqual(destination.placements[0][1], 'all-purpose')
        self.assertEqual(destination.placed_as, 'ammo')

    def test_battery_pack_moves_an_all_purpose_counter_not_a_charge_counter(self):
        module = importlib.import_module('cards.pack.gmw.rocket_raccoon.16034')
        ability = module.GetAbilities()[1]
        source = Mock()
        target = Mock()
        effect = SimpleNamespace(
            this=SimpleNamespace(CastTo=lambda _type: source),
            targets=[SimpleNamespace(CastTo=lambda _type: target)],
        )

        with patch.object(module.Faces, 'MoveCounters', return_value=1) as move:
            ability.operation(effect, Mock())

        move.assert_called_once_with(source, target, 1, 'all-purpose', effect)
        self.assertFalse(any(isinstance(cost, CostFunc.Counter) for cost in ability.cost_funcs))

    def test_dash_is_immutable_and_compares_as_zero(self):
        attribute = object.__new__(HasAttribute)
        attribute.attributes = {'ATK': ('printed_attack', int)}
        attribute.non_numerical_attributes = set()
        attribute.printed_attack = 4
        attribute.player_num = 1

        HasAttribute.InitPrintedValue(attribute, 'ATK', '—')

        self.assertEqual(attribute.printed_attack, 0)
        self.assertEqual(attribute.non_numerical_attributes, {'ATK'})

        face = object.__new__(CardFace)
        face.non_numerical_attributes = {'ATK'}
        self.assertEqual(CardFace.GetKeyword(face, 'ATK'), 0)

    def test_same_named_encounter_sets_from_different_packs_are_distinct(self):
        first = Paper('a', '', 'Treachery', False, 'Test', pack='pack_one', set_name='Shared Set')
        second = Paper('b', '', 'Treachery', False, 'Test', pack='pack_two', set_name='Shared Set')

        self.assertNotEqual(
            first.GetEncounterSetIdentity(),
            second.GetEncounterSetIdentity(),
        )

    def test_per_player_value_is_converted_before_a_gets_hit_point_modifier(self):
        unit = Mock()
        unit.card.state.is_advancing = False
        unit.card.state.is_leaving_play = False
        unit.card.state.is_flipping = False
        unit.health = 1
        effect = SimpleNamespace(this=SimpleNamespace(card=SimpleNamespace(state=SimpleNamespace(is_leaving_play=False))))
        gain = object.__new__(ModelGain)
        gain.GetThis = lambda: unit

        with patch('game.card.face.attribute.can_health.CanHealth.IsType', return_value=True), \
            patch('game.card.face.base.Unit2.IsType', return_value=True), \
            patch.object(Worlds, 'ConvertPerPlayerIconToInt', return_value=4):
            ModelGain.Gain(gain, effect, 1, health='2*')

        unit.GainHealthAndMaxHealth.assert_called_once_with(4, effect)

    def test_gets_stat_effects_apply_and_revert_from_the_same_base_value(self):
        unit = Mock()
        unit.card.state.is_advancing = False
        gain = object.__new__(ModelGain)
        gain.GetThis = lambda: unit
        effect = object()

        with patch('game.card.face.attribute.can_attack.HasAttack.IsType', return_value=True):
            ModelGain.Gain(gain, effect, 1, attack=2)
            ModelGain.Gain(gain, effect, -1, attack=2)

        self.assertEqual(
            [call.args for call in unit.GainAttack.call_args_list],
            [(2, effect), (-2, effect)],
        )

    def test_undefined_or_blanked_variable_is_zero(self):
        face = SimpleNamespace(
            non_numerical_attributes=set(),
            ignore_keywords={},
            is_treat_as_if_blank=False,
            keywords={},
        )

        self.assertEqual(CardFace.GetKeyword(face, 'ATK'), 0)

    def test_moving_damage_off_a_character_uses_healing_semantics(self):
        source = SimpleNamespace(
            GetLostHealth=lambda: 2,
            HealHealth=Mock(),
        )
        target = SimpleNamespace(TakeDamage=Mock())
        effect = SimpleNamespace(ability=SimpleNamespace(IsLabel=lambda _label: False))

        CanHealth.MoveDamage(source, 5, target, effect)

        source.HealHealth.assert_called_once_with(2, effect)
        target.TakeDamage.assert_called_once_with(source, 2, effect)

    def test_moving_threat_off_a_scheme_uses_remove_threat_semantics(self):
        source = SimpleNamespace(
            RemoveThreatInternal=Mock(return_value=3),
            PlaceThreatOnSchemes=Mock(),
        )
        target = object()
        effect = object()

        moved = Scheme2.MoveThreat(source, 4, effect, [target])

        self.assertEqual(moved, 3)
        source.RemoveThreatInternal.assert_called_once_with(source, 4, effect)
        source.PlaceThreatOnSchemes.assert_called_once_with([target], 3, effect)

    def test_losing_max_hit_points_checks_for_defeat_after_health_changes(self):
        unit = SimpleNamespace(
            UpdateHealth=Mock(),
            LimitHealth=Mock(),
        )
        effect = object()

        CanHealth.GainOnlyHealth(unit, -2, effect)

        unit.UpdateHealth.assert_called_once_with(-2, effect)
        unit.LimitHealth.assert_called_once_with(effect)

    def test_steady_requires_two_status_cards_before_the_status_applies(self):
        steady_card = SimpleNamespace(CastTo=lambda _type: SimpleNamespace(IsSteady=lambda: True))
        one_status = SimpleNamespace(card=steady_card, stunned=1)
        two_statuses = SimpleNamespace(card=steady_card, stunned=2)

        self.assertFalse(CanStatus.IsStunned(one_status))
        self.assertTrue(CanStatus.IsStunned(two_statuses))

    def test_status_placement_is_broadcast_for_vulnerable_forced_interrupt(self):
        status_face = object()
        unit = SimpleNamespace(
            card=SimpleNamespace(IsOnField=lambda: True),
            CanbeStunned=lambda: True,
            CanbeConfused=lambda: True,
            IsTough=lambda: False,
            components=SimpleNamespace(status=SimpleNamespace(GiveStatusCard=Mock(return_value=status_face))),
            CastTo=lambda _type: SimpleNamespace(IsVulnerable=lambda: True),
            IsStunned=lambda: True,
            IsConfused=lambda: False,
        )
        would_message = Mock()
        would_message.is_be_instead = False
        effect = object()

        with patch('game.message.Message.WhenStatusWouldCardPlaceOn', return_value=would_message), \
            patch('game.message.Message.AfterStatusCardPlaceOn') as after, \
            patch.object(Faces, 'DiscardAll') as discard:
            self.assertTrue(CanStatus.GainStatus(unit, 'Stunned', effect))

        after.return_value.Send.assert_called_once()
        discard.assert_not_called()

    def test_cannot_is_absolute_unless_card_text_explicitly_overrides_it(self):
        status_face = object()
        unit = SimpleNamespace(
            card=SimpleNamespace(IsOnField=lambda: True),
            CanbeStunned=lambda: False,
            IsStunned=lambda: False,
            components=SimpleNamespace(status=SimpleNamespace(GiveStatusCard=Mock(return_value=status_face))),
            CastTo=lambda _type: SimpleNamespace(IsVulnerable=lambda: False),
        )
        would_message = Mock(is_be_instead=False)
        effect = object()

        self.assertFalse(CanStatus.GainStatus(unit, 'Stunned', effect))

        with patch('game.message.Message.WhenStatusWouldCardPlaceOn', return_value=would_message), \
            patch('game.message.Message.AfterStatusCardPlaceOn') as after:
            self.assertTrue(CanStatus.GainStatus(unit, 'Stunned', effect, override_cannot=True))

        unit.components.status.GiveStatusCard.assert_called_once_with('Stunned', effect)
        after.return_value.Send.assert_called_once()

    def test_reset_clears_all_counter_and_token_types(self):
        parent = SimpleNamespace()
        counters = Counter(parent)
        tokens = Token(parent)
        counters.SetCounters(2, 'charge')
        tokens.SetTokens(3, 'threat')
        tokens.SetTokens(2, 'infamy')

        counters.OnParentReset()
        tokens.OnParentReset()

        self.assertEqual(counters.GetAllCounters(), 0)
        self.assertEqual(tokens.GetAllTokens(), 0)

    def test_end_phase_readies_encounter_cards_once(self):
        player = Mock()
        player.is_eliminated = False
        player.GetControlCards.return_value = []
        player.world.GetFirstPlayer.return_value = player
        player.GetIdentity.return_value.card.game_area = object()
        encounter = object()
        player_card = object()
        phase = object.__new__(PlayerPhase)
        phase.player = player

        with patch.object(PlayerPhase, 'MayDiscardHandCardsAndDrawUpToMax'), \
            patch('game.effect.rule.EndPhase', return_value=object()), \
            patch('game.operate.worlds.Worlds.GetOnFieldCards', return_value=[encounter, player_card]), \
            patch('game.card.face.base.EncounterCard.IsType', side_effect=lambda face: face is encounter), \
            patch.object(Faces, 'ReadyAll') as ready:
            PlayerPhase.EndPhase(phase)

        ready_faces = ready.call_args.args[0]
        self.assertEqual(ready_faces, [encounter])

    def test_find_in_play_sees_environments_across_split_game_areas_only_faceup(self):
        local_area = SimpleNamespace()
        remote_area = SimpleNamespace()

        def face(game_area, *, faceup=True):
            result = Mock()
            result.card = SimpleNamespace(game_area=game_area)
            result.IsFaceUp.return_value = faceup
            result.GetInventoryDeck.return_value = _Deck()
            result.GetPlacedCardArea.return_value = _Deck()
            return result

        local_environment = face(local_area)
        remote_environment = face(remote_area)
        dealt_facedown = face(local_area, faceup=False)
        boost_facedown = face(local_area, faceup=False)

        def player(game_area, environment):
            identity = SimpleNamespace(card=SimpleNamespace(GetGameArea=lambda: game_area))
            empty = _Deck()
            return SimpleNamespace(
                area_hero=SimpleNamespace(GetSize=lambda: 1, GetAll=lambda: []),
                area_environment=_Deck(environment),
                allies=empty,
                supports=empty,
                engaged_minions=empty,
                obligations_area=empty,
                dealt_encounter_cards=_Deck(dealt_facedown),
                GetIdentity=lambda: identity,
            )

        local_player = player(local_area, local_environment)
        remote_player = player(remote_area, remote_environment)
        villain = face(local_area)
        villain.BoostCardsDeck = _Deck(boost_facedown)
        world = SimpleNamespace(
            const_players=[local_player, remote_player],
            area_schemes_main=_Deck(),
            area_schemes_side=_Deck(),
            area_environment=_Deck(),
            scenario=SimpleNamespace(area_villain=_Deck(villain)),
        )
        local_area.world = world
        remote_area.world = world

        effect = SimpleNamespace(world=world)
        with patch.object(Worlds, 'CastGameArea', return_value=local_area), \
            patch('game.operate.search_internal.SearchInternal.SearchForCardsInternal',
                  side_effect=lambda _effect, _player, faces, **_kwargs: list(faces)):
            found = Search.SearchForCards(
                effect,
                local_player,
                include_in_play=True,
                not_move=True,
            )

        self.assertIn(local_environment, found)
        self.assertIn(remote_environment, found)
        self.assertNotIn(dealt_facedown, found)
        self.assertNotIn(boost_facedown, found)

    def test_attach_to_uses_the_destination_specified_by_the_effect(self):
        inventory = object()
        target = SimpleNamespace(
            card=SimpleNamespace(IsOnField=lambda: True),
            GetInventoryDeck=lambda: inventory,
        )
        card_area = SimpleNamespace(UnMarkAsRemoved=Mock())
        attachment = SimpleNamespace(
            card=SimpleNamespace(area=card_area),
            bind_face=None,
            refers_to_the_villain_refers_to_attached=True,
            OnAttachTo=Mock(),
        )
        would_message = Mock(is_be_instead=False)
        effect = object()

        with patch('game.message.Message.WhenCardWouldAttachTo', return_value=would_message), \
            patch('game.message.Message.AfterCardAttachTo') as after, \
            patch('game.effect.rule.GameRule', return_value=object()), \
            patch.object(Faces, 'MoveAllTo', return_value=[attachment]) as move:
            attached = CanAttach.AttachTo2(attachment, target, effect)

        self.assertTrue(attached)
        move.assert_called_once()
        self.assertIs(move.call_args.args[1], inventory)
        attachment.OnAttachTo.assert_called_once_with(target, False)
        after.return_value.Send.assert_called_once()

    def test_temporary_minion_becomes_an_ally_under_the_resolving_player_control(self):
        player = object()
        shared_card = Mock()
        minion = Mock()
        minion.card = shared_card
        shared_card.CastTo.return_value = minion
        minion.pic_id = 'pic'
        minion.printed_name = 'Captured Minion'
        minion.printed_subtitle = ''
        minion.printed_attack = 2
        minion.printed_scheme = 1

        ally = Mock()
        ally.card = shared_card
        ally.effect.RegisterTemp.side_effect = [[], []]
        effect = SimpleNamespace(this=object(), world=object())
        paper = object()

        with patch('game.card.factory.CardFactory.FindCardPapers', return_value=[paper]), \
            patch('game.card.factory.CardFactory.CreateFace', return_value=ally), \
            patch('game.card.factory.CardFactory.FaceRegisterEffects'), \
            patch('game.card.face.card_type.Ally.IsType', return_value=True), \
            patch('game.ability.factory.AbilityFactory.AfterCardLeavePlay', return_value=object()), \
            patch('game.ability.factory.AbilityFactory.WhenCardLeavePlay', return_value=object()):
            treated = Faces.TreatAsAlly(minion, 'Temporary Ally', player, effect)

        self.assertTrue(treated)
        ally.PutIntoPlay.assert_called_once_with(player, effect, under_control=True)
        shared_card.SwapCardFace.assert_called_once_with(ally, effect)

    def test_temporary_ally_becomes_a_minion_engaged_with_its_controller(self):
        engage_player = object()
        shared_card = Mock()
        ally = Mock()
        ally.card = shared_card
        ally.paper.card_id = 'ally-card'
        ally.printed_attack = 2
        ally.printed_thwart = 1

        minion = Mock()
        minion.card = shared_card
        minion.effect.RegisterTemp.side_effect = [[], []]
        minion.ability = Mock()
        shared_card.SwapCardFace.return_value = minion
        this = Mock()
        this.effect.RegisterTemp.return_value = []
        effect = SimpleNamespace(this=this, world=object())
        paper = SimpleNamespace(card_id='temporary-minion', pack='test', set_name='test')

        with patch('game.card.factory.CardFactory.FindCardPapers', return_value=[paper]), \
            patch('game.card.factory.CardFactory.CreateFace', return_value=minion), \
            patch('game.card.factory.CardFactory.FaceRegisterEffects'), \
            patch('cards.database.CardsDB.FindAbilities', return_value=[]), \
            patch('game.card.face.card_type.Ally.IsType', return_value=True), \
            patch('game.card.face.card_type.Hero.IsType', return_value=False), \
            patch('game.card.face.card_type.Minion.IsType', return_value=True), \
            patch('game.ability.factory.AbilityFactory.AfterCardLeavePlay', return_value=object()), \
            patch('game.ability.factory.AbilityFactory.WhenCardLeavePlay', return_value=object()), \
            patch('game.ability.factory.AbilityFactory.WhenCardTreatAsIfBlank', return_value=object()):
            treated = TreatAsMinion(ally, 'Temporary Minion', engage_player, effect)

        self.assertTrue(treated)
        minion.PutIntoPlay.assert_called_once_with(engage_player, effect)
        shared_card.SwapCardFace.assert_called_once_with(minion, effect)


if __name__ == '__main__':
    unittest.main()
