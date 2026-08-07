from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

# Preserve the application's normal import ordering.
from engine import Engine

from game.ability.factory.friend import AbilityFactoryFriend
from game.card.card import Card
from game.deck.deck import Deck2
from game.effect.effect_failure import EffectFailure
from game.operate.worlds import Worlds
from game.selector import Select
from game.world.limit_monitor.player_side_scheme_limit import PlayerSideSchemeLimit


class _PopDeck:

    def __init__(self, faces):
        self.faces = list(faces)
        self.flags = SimpleNamespace(is_deck=True)
        self.world = SimpleNamespace(is_game_over=False)
        self.owner = SimpleNamespace(is_eliminated=False)
        self.shuffle_with_discard_count = 0

    def GetOwner(self):
        return self.owner

    def GetSize(self):
        return len(self.faces)

    def Get(self, from_top=True):
        return list(self.faces)


class V18TargetRepeatTests(unittest.TestCase):

    def test_same_target_cannot_be_selected_twice_by_default(self):
        face = Mock()
        face.card = Mock()
        selector = Select.From(faces=[face], range=(2, 2))
        effect = SimpleNamespace(failures=Mock())

        self.assertFalse(
            selector.AfterSelectTargets(effect, [face, face], (2, 2)),
        )
        effect.failures.Set.assert_called_once_with(
            None,
            EffectFailure.DuplicateTarget,
        )

    def test_explicit_repeat_rule_allows_the_same_target(self):
        face = Mock()
        face.card = Mock()
        selector = Select.From(
            faces=[face],
            range=(2, 2),
            repeat_rules='Any',
        )

        self.assertTrue(
            selector.AfterSelectTargets(
                SimpleNamespace(failures=Mock()),
                [face, face],
                (2, 2),
            ),
        )


class V18EncounterResetTests(unittest.TestCase):

    def test_multi_card_effect_continues_after_encounter_deck_reset(self):
        first = object()
        second = object()
        deck = _PopDeck([first])

        def process(face):
            deck.faces.remove(face)
            if face is first:
                deck.shuffle_with_discard_count += 1
                deck.faces.append(second)

        result = Deck2.PopInternal(
            deck,
            2,
            process,
            object(),
            continue_after_shuffle=True,
        )

        self.assertEqual(result, [first, second])

    def test_discard_encounter_cards_requests_continue_after_reset(self):
        deck = Mock()
        deck.DiscardCardsInternal.return_value = []
        effect = Mock()

        with patch.object(Worlds, 'GetEncounterDeck', return_value=deck), \
             patch.object(Worlds, 'ConvertPerPlayerIconToInt', return_value=3):
            Worlds.DiscardEncounterCards(3, effect)

        deck.DiscardCardsInternal.assert_called_once_with(
            3,
            effect,
            continue_after_shuffle=True,
            each_time=None,
        )

    def test_discard_until_continues_into_reset_encounter_deck(self):
        first = Mock()
        second = Mock()
        deck = _PopDeck([first])

        def discard_first(effect):
            deck.faces.remove(first)
            deck.shuffle_with_discard_count += 1
            deck.faces.append(second)

        def discard_second(effect):
            deck.faces.remove(second)

        first.DiscardInternal.side_effect = discard_first
        second.DiscardInternal.side_effect = discard_second
        finder = Mock()
        finder.Check.side_effect = [False, True]
        moved_message = Mock()

        with patch('game.card.card_finder.CardFinder', return_value=finder), \
             patch(
                 'game.message.Message.AfterCardsMoved',
                 return_value=moved_message,
             ):
            found, discarded = Deck2.DiscardUntil(
                deck,
                object(),
                name=None,
                trait=None,
                card_type='CardFace',
            )

        self.assertIs(found, second)
        self.assertEqual(discarded, [first])
        moved_message.Send.assert_called_once()


class V18PlayerSideSchemeLimitTests(unittest.TestCase):

    def test_excess_scheme_is_discarded_after_entering_play_not_defeated(self):
        schemes = [Mock(), Mock()]
        discarded_scheme = schemes[0]
        for scheme in schemes:
            scheme.paper.IsFromSet.return_value = False
        area = Mock()
        area.Get.side_effect = lambda face_up: list(schemes)
        identity = Mock()
        player = Mock()
        player.GetIdentity.return_value = identity
        world = SimpleNamespace(
            started_player_num=1,
            is_game_over=False,
            area_schemes_side=area,
            GetFirstPlayer=lambda: player,
        )
        monitor = PlayerSideSchemeLimit(world)

        def choose(rule, ability):
            effect = SimpleNamespace(
                targets=[schemes[0]],
                GetPaidResources=lambda: Mock(),
            )
            ability.operation(effect, Mock())

        player.ChooseAbilities.side_effect = choose

        def discard(targets, effect):
            schemes.remove(targets[0])
            return list(targets)

        with patch(
            'game.card.face.card_type.PlayerSideScheme.IsType',
            return_value=True,
        ), patch(
            'game.effect.rule.GameRule',
            return_value=object(),
        ), patch(
            'game.operate.faces.Faces.DiscardAll',
            side_effect=discard,
        ) as discard_all:
            self.assertTrue(monitor.CheckLimit())

        discard_all.assert_called_once()
        discarded_scheme.Defeated.assert_not_called()


class V18RemovedFromGameTests(unittest.TestCase):

    def MakeCard(self):
        def flags():
            return SimpleNamespace(
                is_in_play=False,
                is_boost_area=False,
                is_dealt_encounter=False,
                is_place_card_area=False,
                is_revealing=False,
            )

        removed = SimpleNamespace(
            name='removed',
            flags=flags(),
        )
        destination = SimpleNamespace(
            name='destination',
            flags=flags(),
        )
        world = SimpleNamespace(
            area_removed=removed,
            is_game_over=True,
            is_game_started=False,
        )
        face = Mock()
        card = object.__new__(Card)
        card.world = world
        card.area = removed
        card.face = face
        card.owner_internal = SimpleNamespace(is_eliminated=False)
        card.state = SimpleNamespace(is_leaving_play=False)
        card.can_state = Mock()
        card.is_apply_unique_rule = None
        face.card = card
        face.OnWhenCardWouldMoveToArea.return_value = True
        return card, face, removed, destination

    def test_generic_effect_cannot_return_removed_card(self):
        card, _, _, destination = self.MakeCard()
        effect = SimpleNamespace(
            context=SimpleNamespace(allowed_removed_cards=set()),
        )

        self.assertFalse(card.CheckIfCanMove(destination, effect))

    def test_explicit_removed_area_search_allows_selected_card_to_move(self):
        card, face, removed, destination = self.MakeCard()
        effect = SimpleNamespace(
            context=SimpleNamespace(allowed_removed_cards={card}),
        )
        move_message = SimpleNamespace(into_area=destination)

        with patch(
            'game.message.Message.WhenCardWouldMoveToArea',
            return_value=move_message,
        ):
            result = card.CheckIfCanMove(destination, effect)

        self.assertIs(result, move_message)
        face.OnWhenCardWouldMoveToArea.assert_called_once_with(move_message)


class V18BasicPowerAuditTests(unittest.TestCase):

    def test_basic_attack_and_thwart_still_require_exhaustion(self):
        exhaust_cost = object()
        with patch(
            'game.ability.cost_func.CostFunc.Exhaust',
            return_value=exhaust_cost,
        ):
            attack = AbilityFactoryFriend.ThisCanAttack()
            thwart = AbilityFactoryFriend.ThisCanThwart()

        self.assertIn(exhaust_cost, attack.cost_funcs)
        self.assertIn(exhaust_cost, thwart.cost_funcs)


if __name__ == '__main__':
    unittest.main()
