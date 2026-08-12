from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

# Preserve the application's normal import ordering.
from engine import Engine  # noqa: F401

from game.ability.factory import AbilityFactory
from game.card.card_finder import CardFinder
from game.message import Message
from game.message.message import Message2


class ThwartRestrictionTests(unittest.TestCase):

    def test_can_only_thwart_this_is_a_global_restriction(self):
        ability = AbilityFactory.UnitCannotThwartTarget(
            CardFinder(name="Hope Summers"),
            can_only_thwart="This",
        )[0]

        self.assertFalse(ability.is_local)

    def test_can_only_thwart_rejects_every_other_scheme(self):
        grasp = Mock()
        hope = Mock()
        other_scheme = Mock()
        effect = SimpleNamespace(this=grasp)
        message = SimpleNamespace(
            who_thwart=hope,
            scheme=other_scheme,
            SetCannotBeThwart=Mock(),
        )
        ability = AbilityFactory.UnitCannotThwartTarget(
            CardFinder(name="Hope Summers"),
            can_only_thwart="This",
        )[0]

        def matches(rule, face, from_effect):
            if rule is None:
                return True
            if isinstance(rule, CardFinder):
                return face is hope
            if rule == "This":
                return face is grasp
            return False

        with patch(
            "game.ability.condition.Condition.CheckWhichCard",
            side_effect=matches,
        ):
            self.assertTrue(all(
                condition(effect, message)
                for condition in ability.const_condition
            ))
            ability.operation(effect, message)

        message.SetCannotBeThwart.assert_called_once_with(effect)

    def test_can_only_thwart_keeps_the_named_scheme_legal(self):
        grasp = Mock()
        hope = Mock()
        effect = SimpleNamespace(this=grasp)
        message = SimpleNamespace(
            who_thwart=hope,
            scheme=grasp,
        )
        ability = AbilityFactory.UnitCannotThwartTarget(
            CardFinder(name="Hope Summers"),
            can_only_thwart="This",
        )[0]

        def matches(rule, face, from_effect):
            if rule is None:
                return True
            if isinstance(rule, CardFinder):
                return face is hope
            if rule == "This":
                return face is grasp
            return False

        with patch(
            "game.ability.condition.Condition.CheckWhichCard",
            side_effect=matches,
        ):
            self.assertFalse(all(
                condition(effect, message)
                for condition in ability.const_condition
            ))


class SchemeDefeatPresentationTests(unittest.TestCase):

    def test_scheme_defeat_is_presented_once_across_timing_messages(self):
        world = SimpleNamespace(
            is_game_over=False,
            object_manager=Mock(),
        )
        world.object_manager.AddObject.side_effect = range(1, 10)
        scheme = Mock()
        scheme.card.world = world
        source = Mock()
        by_effect = SimpleNamespace(this=source, initiator=None)

        with patch.object(Message2, "Present") as present:
            would = Message.WhenSchemeWouldBeDefeated(
                scheme,
                by_effect,
                None,
                None,
            )
            defeated = Message.WhenSchemeBeDefeated(
                scheme,
                would,
                False,
            )
            Message.AfterSchemeBeDefeated(scheme, by_effect, defeated)

        self.assertEqual(present.call_count, 1)


if __name__ == "__main__":
    unittest.main()
