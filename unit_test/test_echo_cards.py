from __future__ import annotations

import importlib
from unittest import TestCase
from unittest.mock import Mock, patch

# Match the application's normal import order without starting the server.
from engine import Engine


class DaredevilAllyDiscountTests(TestCase):

    def test_played_event_cleanup_cannot_unregister_discount_twice(self):
        module = importlib.import_module("cards.pack.fne.echo.60039")
        response = module.GetAbilities()[0]

        cost_effect = Mock(is_unregister=False)
        cleanup_effect = Mock()
        daredevil = Mock()
        daredevil.effect.RegisterTemp.side_effect = [
            [cost_effect],
            [cleanup_effect],
        ]

        effect = Mock()
        effect.this.CastTo.return_value = daredevil
        effect.GetInitiator.return_value = Mock()

        response.operation(effect, Mock())

        discount_registration = daredevil.effect.RegisterTemp.call_args_list[0]
        self.assertFalse(discount_registration.kwargs["unregister_after_exec"])
        self.assertTrue(discount_registration.kwargs["until_round_end"])

        cleanup_ability = daredevil.effect.RegisterTemp.call_args_list[1].args[0]
        played_message = Mock()
        played_message.play_effect.ability.is_play = True

        with patch.object(module.Effects, "UnRegister") as unregister:
            cleanup_ability.operation(Mock(), played_message)
            unregister.assert_called_once_with([cost_effect])

            cost_effect.is_unregister = True
            cleanup_ability.operation(Mock(), played_message)
            unregister.assert_called_once_with([cost_effect])


class RaisedByTheKingpinTests(TestCase):

    def test_ongoing_effects_use_the_player_given_the_obligation(self):
        module = importlib.import_module("cards.pack.fne.echo.60060")
        abilities = module.GetAbilities()
        maya = Mock()
        obligation = Mock()
        obligation.GetGaveToPlayer.return_value = maya
        effect = Mock()
        effect.this.CastTo.return_value = obligation
        message = Mock()
        message.by_effect.GetInitiator.return_value = maya

        for ability in abilities[1:]:
            with self.subTest(event=ability.when.__name__):
                self.assertTrue(ability.conditions[-1](effect, message))

        obligation.GetGaveToPlayer.assert_called()
        effect.this.GetControlByPlayer.assert_not_called()

    def test_other_players_do_not_advance_or_bypass_the_obligation(self):
        module = importlib.import_module("cards.pack.fne.echo.60060")
        abilities = module.GetAbilities()
        obligation = Mock()
        obligation.GetGaveToPlayer.return_value = Mock(name="Maya")
        effect = Mock()
        effect.this.CastTo.return_value = obligation
        message = Mock()
        message.by_effect.GetInitiator.return_value = Mock(name="Other player")

        for ability in abilities[1:]:
            with self.subTest(event=ability.when.__name__):
                self.assertFalse(ability.conditions[-1](effect, message))
