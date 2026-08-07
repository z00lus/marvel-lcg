from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

# Preserve the application's normal import ordering.
from engine import Engine

from game.card.face.attribute.can_surge import CanSurge
from game.player.action.player_action import PlayerAction


class V18SurgeQueueTests(unittest.TestCase):

    def test_surge_deals_one_facedown_card_without_revealing_it(self):
        source = SimpleNamespace(surge=1)
        player = Mock()
        would_surge = Mock(is_be_instead=False)
        surge_effect = object()

        with patch(
            'game.message.Message.WhenSurgeWouldBeResolved',
            return_value=would_surge,
        ), patch(
            'game.effect.rule.Surge',
            return_value=surge_effect,
        ):
            result = CanSurge.ResolveSurge(source, player)

        would_surge.Send.assert_called_once_with()
        player.DealEncounterCards.assert_called_once_with(1, surge_effect)
        self.assertIs(result, surge_effect)

    def test_canceling_surge_prevents_the_extra_card(self):
        source = SimpleNamespace(surge=1)
        player = Mock()
        would_surge = Mock(is_be_instead=True)

        with patch(
            'game.message.Message.WhenSurgeWouldBeResolved',
            return_value=would_surge,
        ):
            result = CanSurge.ResolveSurge(source, player)

        self.assertIsNone(result)
        player.DealEncounterCards.assert_not_called()

    def test_dealt_cards_are_appended_to_the_fifo_queue(self):
        player = SimpleNamespace(dealt_encounter_cards=object())
        action = SimpleNamespace(GetPlayer=lambda: player)
        face = object()
        effect = object()
        would_deal = Mock(is_be_instead=False)
        after_deal = Mock()

        with patch(
            'game.message.Message.WhenPlayerWouldBeDealtEncounterCard',
            return_value=would_deal,
        ), patch(
            'game.message.Message.AfterPlayerDealEncounterCard',
            return_value=after_deal,
        ), patch(
            'game.operate.faces.Faces.MoveAllToDeck',
        ) as move:
            PlayerAction.DealEncounterCard(action, face, effect)

        move.assert_called_once_with(
            [face],
            player.dealt_encounter_cards,
            'Bottom',
            effect,
        )
        after_deal.Send.assert_called_once_with()

    def test_card_dealt_outside_villain_phase_stays_facedown(self):
        face = Mock()
        player = SimpleNamespace(
            world=SimpleNamespace(
                is_game_over=False,
                phase=SimpleNamespace(state='Player Turn'),
            ),
        )
        action = SimpleNamespace(
            GetPlayer=lambda: player,
            DealEncounterCard=Mock(),
        )
        effect = object()

        def pop_one(size, callback, continue_after_shuffle, by_effect):
            callback(face)

        with patch(
            'game.operate.worlds.Worlds.PopEncounterCards',
            side_effect=pop_one,
        ):
            PlayerAction.DealEncounterCards(action, 1, effect)

        action.DealEncounterCard.assert_called_once_with(face, effect)
        face.Reveal.assert_not_called()

    def test_chained_surge_waits_for_original_responses_and_keeps_deal_order(self):
        log = []

        class Queue:
            def __init__(self):
                self.faces = []

            def GetSize(self):
                return len(self.faces)

            def GetTop(self):
                return self.faces[-1] if self.faces else None

            def DealLast(self, face):
                self.faces.insert(0, face)

            def Remove(self, face):
                self.faces.remove(face)

            def DiscardAll(self, effect):
                self.faces.clear()

        queue = Queue()
        player = SimpleNamespace(
            dealt_encounter_cards=queue,
            world=SimpleNamespace(is_game_over=False),
            is_eliminated=False,
            stat=SimpleNamespace(RecordReveal=lambda face: None),
            GetIdentity=lambda: object(),
        )
        action = SimpleNamespace(GetPlayer=lambda: player)

        first = Mock()
        second = Mock()
        third = Mock()

        def reveal_first(player, effect):
            queue.Remove(first)
            log.append('first reveal')
            queue.DealLast(third)
            log.append('first responses')

        def reveal_second(player, effect):
            queue.Remove(second)
            log.append('second reveal')

        def reveal_third(player, effect):
            queue.Remove(third)
            log.append('surge reveal')

        first.Reveal.side_effect = reveal_first
        second.Reveal.side_effect = reveal_second
        third.Reveal.side_effect = reveal_third
        # First and second were dealt in that order. The chained Surge card is
        # dealt while first resolves, so it must remain behind second.
        queue.faces = [second, first]

        with patch('game.effect.rule.GameRule', return_value=object()):
            PlayerAction.RevealEncounterCards(action)

        self.assertEqual(
            log,
            [
                'first reveal',
                'first responses',
                'second reveal',
                'surge reveal',
            ],
        )


if __name__ == '__main__':
    unittest.main()
