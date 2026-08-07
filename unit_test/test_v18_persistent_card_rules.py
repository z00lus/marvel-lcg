from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

# Preserve the application's normal import ordering.
from engine import Engine

from game.card.face.attribute.has_permanent import HasPermanent
from game.card.face.model.face_on_event import ModelOnEvent
from game.player.limit_monitor.restricted_limit import RestrictedLimit


class V18PermanentRulesTests(unittest.TestCase):

    def MakePermanent(self):
        face = object.__new__(HasPermanent)
        face.paper = SimpleNamespace(set_name='permanent-set')
        face.consider_as = SimpleNamespace(card_types={})
        face.keywords = {'Permanent': {face: 1}}
        face.ignore_keywords = {}
        face.GetBuff = lambda buff_type: False
        owner = SimpleNamespace(is_eliminated=False)
        card = SimpleNamespace(
            state=SimpleNamespace(is_discarding=False),
            area=object(),
            Discard=Mock(return_value=True),
            GetOwner=lambda: owner,
        )
        face.card = card
        return face, card

    def test_permanent_card_cannot_be_discarded_by_an_unrelated_effect(self):
        face, card = self.MakePermanent()
        effect = SimpleNamespace(
            this=SimpleNamespace(
                paper=SimpleNamespace(set_name='unrelated-set'),
            ),
        )

        self.assertFalse(face.DiscardInternal(effect))

        card.Discard.assert_not_called()
        self.assertFalse(card.state.is_discarding)

    def test_permanent_card_rejects_an_unrelated_leave_play_move(self):
        face, _ = self.MakePermanent()
        effect = SimpleNamespace(
            this=SimpleNamespace(
                paper=SimpleNamespace(set_name='unrelated-set'),
            ),
        )
        message = SimpleNamespace(by_effect=effect)

        with patch.object(
            ModelOnEvent,
            'OnWhenCardLeavePlay',
            return_value=True,
        ) as normal_leave, patch.object(
            HasPermanent,
            'GetBindFace',
            return_value=None,
        ):
            self.assertFalse(face.OnWhenCardLeavePlay(message))

        normal_leave.assert_not_called()


class V18RestrictedRulesTests(unittest.TestCase):

    def MakePlayer(self, controlled):
        identity = SimpleNamespace(
            GetInventoryDeck=lambda: SimpleNamespace(Get=lambda: list(controlled)),
        )
        return SimpleNamespace(
            is_eliminated=False,
            world=SimpleNamespace(is_game_over=False),
            GetIdentity=lambda: identity,
            ChooseAbilities=Mock(),
        )

    def test_two_restricted_upgrades_are_legal_without_a_discard(self):
        controlled = [
            SimpleNamespace(restricted=1),
            SimpleNamespace(restricted=1),
        ]
        player = self.MakePlayer(controlled)
        monitor = RestrictedLimit(player, 2)

        with patch(
            'game.card.face.card_type.Upgrade.IsType',
            return_value=True,
        ):
            self.assertTrue(monitor.CheckLimit([]))

        self.assertEqual(monitor.curr_restricted, 2)
        player.ChooseAbilities.assert_not_called()

    def test_third_restricted_upgrade_forces_one_to_be_discarded(self):
        controlled = [
            SimpleNamespace(restricted=1),
            SimpleNamespace(restricted=1),
            SimpleNamespace(restricted=1),
        ]
        player = self.MakePlayer(controlled)
        monitor = RestrictedLimit(player, 2)
        finder = Mock()
        finder.Checks.side_effect = lambda faces: list(faces)
        choice = Mock()
        choice.SetTarget.return_value = choice

        def choose_and_discard(*args, **kwargs):
            controlled.pop()
            return [object()]

        player.ChooseAbilities.side_effect = choose_and_discard

        with patch(
            'game.card.face.card_type.Upgrade.IsType',
            return_value=True,
        ), patch(
            'game.card.card_finder.CardFinder',
            return_value=finder,
        ), patch(
            'game.effect.rule.GameRule',
            return_value=object(),
        ), patch(
            'game.ability.factory.AbilityFactory.ForChoiceAbility',
            return_value=choice,
        ):
            self.assertTrue(monitor.CheckLimit([]))

        self.assertEqual(len(controlled), 2)
        self.assertEqual(player.ChooseAbilities.call_count, 1)


class V18FlipResetTests(unittest.TestCase):

    def test_flip_resets_only_the_incoming_faces_keywords_and_model(self):
        old_effect = object()
        new_effect = object()
        old_face = Mock(effects=[old_effect])
        new_face = Mock(effects=[new_effect])
        new_face.card.ui = Mock()
        wrapper = SimpleNamespace(GetThis=lambda: new_face)

        ModelOnEvent.OnFlip(wrapper, object(), old_face)

        new_face.card.ui.ResetEffectedBy.assert_called_once()
        new_face.ResetKeywords.assert_called_once()
        new_face.OnResetModel.assert_called_once()
        old_face.ResetKeywords.assert_not_called()
        self.assertEqual(new_face.effects, [new_effect])
        self.assertEqual(old_face.effects, [old_effect])


if __name__ == '__main__':
    unittest.main()
