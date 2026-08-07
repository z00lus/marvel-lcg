from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

# Preserve the application's normal import ordering.
from engine import Engine

from game.operate.faces import Faces


class _Area:

    def __init__(self, *, in_play=False, in_hand=False, deck=False):
        self.cards = []
        self.flags = SimpleNamespace(
            is_in_play=in_play,
            is_in_hand=in_hand,
            is_deck=deck,
        )

    def GetIndex(self, face):
        return self.cards.index(face.card)

    def Remove(self, card):
        self.cards.remove(card)

    def Insert(self, index, card):
        card.area = self
        self.cards.insert(index, card)


class _Component:

    def __init__(self, card, *, with_deck=False):
        self.parent = card
        if with_deck:
            self.deck = SimpleNamespace(bind_card=card, bind_owner=card.owner)


class _Card:

    def __init__(self, area, name, *, ready=True, face_up=True):
        self.owner = object()
        self.state = SimpleNamespace(
            is_ready=ready,
            is_face_up=face_up,
            is_leaving_play=False,
        )
        self.face = SimpleNamespace(card=self, name=name)
        self.area = area
        area.cards.append(self)
        self.components = SimpleNamespace(
            inventory=_Component(self, with_deck=True),
            placed_card=_Component(self, with_deck=True),
            status=_Component(self, with_deck=True),
            counter=_Component(self),
            token=_Component(self),
            health=_Component(self),
            boostable=_Component(self, with_deck=True),
        )
        self.allow_move = True
        self.move_calls = []

    def GetOwner(self):
        return self.owner

    def CheckIfCanMove(self, area, effect):
        if not self.allow_move:
            return None
        return SimpleNamespace(
            trigger=self.face,
            from_area=self.area,
            into_area=area,
            by_effect=effect,
        )

    def MoveToAreaInternal(self, message, *, index=-1):
        self.move_calls.append((message.from_area, message.into_area))
        message.from_area.Remove(self)
        message.into_area.Insert(index, self)
        return True


class V18SwapTests(unittest.TestCase):

    def Swap(self, faces):
        message = Mock()
        with patch(
            'game.message.Message.AfterCardsSwapDeck_Text',
            return_value=message,
        ):
            result = Faces.SwapTwoCards(faces, object())
        return result, message

    def test_hand_deck_swap_is_raw_and_inherits_location_orientation(self):
        hand = _Area(in_hand=True)
        deck = _Area(deck=True)
        hand_card = _Card(hand, 'Hand card', ready=False, face_up=True)
        deck_card = _Card(deck, 'Deck card', ready=True, face_up=False)

        result, message = self.Swap([hand_card.face, deck_card.face])

        self.assertTrue(result)
        self.assertIs(deck_card.area, hand)
        self.assertIs(hand_card.area, deck)
        self.assertFalse(deck_card.state.is_ready)
        self.assertTrue(deck_card.state.is_face_up)
        self.assertTrue(hand_card.state.is_ready)
        self.assertFalse(hand_card.state.is_face_up)
        self.assertEqual(hand_card.move_calls, [])
        self.assertEqual(deck_card.move_calls, [])
        message.Send.assert_called_once()

    def test_same_title_play_swap_transfers_location_components_without_lifecycle(self):
        play = _Area(in_play=True)
        deck = _Area(deck=True)
        in_play = _Card(play, 'Same title', ready=False)
        out_of_play = _Card(deck, 'Same title', face_up=False)
        old_health = in_play.components.health
        old_inventory = in_play.components.inventory

        result, _ = self.Swap([in_play.face, out_of_play.face])

        self.assertTrue(result)
        self.assertIs(out_of_play.area, play)
        self.assertIs(out_of_play.components.health, old_health)
        self.assertIs(out_of_play.components.inventory, old_inventory)
        self.assertIs(old_health.parent, out_of_play)
        self.assertIs(old_inventory.deck.bind_card, out_of_play)
        self.assertFalse(out_of_play.state.is_ready)
        self.assertEqual(in_play.move_calls, [])
        self.assertEqual(out_of_play.move_calls, [])

    def test_different_title_play_swap_uses_leave_and_enter_lifecycle(self):
        play = _Area(in_play=True)
        deck = _Area(deck=True)
        in_play = _Card(play, 'Old title', ready=False)
        incoming = _Card(deck, 'New title', face_up=False)
        old_health = in_play.components.health
        incoming_health = incoming.components.health

        result, _ = self.Swap([in_play.face, incoming.face])

        self.assertTrue(result)
        self.assertIs(incoming.area, play)
        self.assertIs(in_play.area, deck)
        self.assertIs(in_play.components.health, old_health)
        self.assertIs(incoming.components.health, incoming_health)
        self.assertEqual(len(in_play.move_calls), 1)
        self.assertEqual(len(incoming.move_calls), 1)
        self.assertFalse(incoming.state.is_ready)

    def test_rejected_lifecycle_swap_moves_neither_card(self):
        play = _Area(in_play=True)
        deck = _Area(deck=True)
        in_play = _Card(play, 'Old title')
        incoming = _Card(deck, 'New title')
        incoming.allow_move = False

        result, message = self.Swap([in_play.face, incoming.face])

        self.assertFalse(result)
        self.assertIs(in_play.area, play)
        self.assertIs(incoming.area, deck)
        self.assertEqual(in_play.move_calls, [])
        self.assertEqual(incoming.move_calls, [])
        message.Send.assert_not_called()

    def test_missing_component_rejects_swap_before_any_move(self):
        hand = _Area(in_hand=True)
        deck = _Area(deck=True)
        hand_card = _Card(hand, 'Hand card')
        deck_card = _Card(deck, 'Deck card')
        deck.cards.remove(deck_card)

        result, message = self.Swap([hand_card.face, deck_card.face])

        self.assertFalse(result)
        self.assertIs(hand_card.area, hand)
        self.assertEqual(hand_card.move_calls, [])
        message.Send.assert_not_called()

    def test_same_deck_swap_preserves_both_positions(self):
        deck = _Area(deck=True)
        first = _Card(deck, 'First')
        second = _Card(deck, 'Second')

        result, _ = self.Swap([first.face, second.face])

        self.assertTrue(result)
        self.assertEqual(deck.cards, [second, first])


if __name__ == '__main__':
    unittest.main()
