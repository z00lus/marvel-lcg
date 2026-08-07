from __future__ import annotations

import importlib
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from engine import Engine


def load_module(path: str):
    return importlib.import_module(path)


class IronManErrataTests(unittest.TestCase):

    def test_tech_bonus_is_capped_at_six_not_total_hand_size(self):
        module = load_module("cards.pack.core.iron_man.01029a")
        sentinel = object()
        with patch.object(
            module.AbilityFactory,
            "ThisGainKeyword",
            return_value=sentinel,
        ) as factory:
            self.assertEqual(module.GetAbilities(), [sentinel])

        get_tech_bonus = factory.call_args.args[0]
        tech_upgrades = [Mock() for _ in range(8)]
        for upgrade in tech_upgrades:
            upgrade.HasTrait.return_value = True
        hero = Mock()
        hero.GetControlByPlayer.return_value.GetControlCardsByType.return_value = tech_upgrades
        effect = Mock()
        effect.this.CastTo.return_value = hero

        # An unrelated +2 hand-size modifier is outside this source's cap.
        external_bonus = 2
        self.assertEqual(get_tech_bonus(effect, []), 6)
        self.assertEqual(external_bonus + get_tech_bonus(effect, []), 8)


class WonderManErrataTests(unittest.TestCase):

    def test_ionic_physiology_tucks_event_even_at_full_health(self):
        module = load_module("cards.pack.wonder_man.58002")
        sentinel = object()
        with patch.object(
            module.AbilityFactory,
            "AfterPlayerPlayedCard",
            return_value=sentinel,
        ) as factory:
            self.assertIs(module.GetAbilities()[2], sentinel)
        operation = factory.call_args.args[3]
        physiology = Mock()
        physiology.TuckCardUnderHere.return_value = True
        physiology.HealthUnits.return_value = False
        identity = Mock()
        event = Mock()
        effect = Mock()
        effect.this.CastTo.return_value = physiology
        effect.GetInitiator.return_value.GetIdentity.return_value = identity

        operation(effect, SimpleNamespace(played_face=event))

        physiology.TuckCardUnderHere.assert_called_once_with([event], effect)
        physiology.HealthUnits.assert_called_once_with([identity], 1, effect)


class ExodusErrataTests(unittest.TestCase):

    def test_uses_attack_snapshot_instead_of_current_atk(self):
        module = load_module("cards.pack.magneto.magneto_nemesis.49028")
        ability = module.GetAbilities()[0]
        exodus = Mock(attack=2)
        player = Mock()
        effect = Mock()
        effect.this.CastTo.return_value = exodus
        message = Mock()
        message.GetAgainstPlayer.return_value = player
        message.atk_messages = [
            SimpleNamespace(
                would_atk_unit_message=SimpleNamespace(attack_damage=7),
            ),
        ]

        ability.operation(effect, message)

        player.DiscardDeckTopCards.assert_called_once_with(7, effect)


class TargetSpotterErrataTests(unittest.TestCase):

    def test_replaces_original_engagement_before_delayed_engagement(self):
        module = load_module("cards.pack.bp.51038")
        ability = module.GetAbilities()[0]
        spotter = Mock()
        player = Mock()
        effect = Mock()
        effect.this.CastTo.return_value = spotter
        effect.GetInitiator.return_value = player
        message = Mock()

        with patch.object(module.RunAt, "AfterEventEnd") as run_after:
            ability.operation(effect, message)

        message.SetBeInstead.assert_called_once_with(effect)
        run_after.assert_called_once()
        delayed_action = run_after.call_args.args[2]
        delayed_action()
        message.minion.EngagePlayer.assert_called_once_with(player, effect)


class ElephantTrunkFaqTests(unittest.TestCase):

    def test_the_trunk_itself_pays_the_required_wakanda_exhaust(self):
        module = load_module("cards.pack.bp.black_panther_shuri.51007")
        ability = module.GetAbilities()[0]

        self.assertEqual(len(ability.cost_funcs), 2)
        mandatory_self, additional_wakanda = ability.cost_funcs
        self.assertEqual(
            mandatory_self.selector.selector_target.raw_target,
            "This",
        )
        self.assertEqual(
            additional_wakanda.selector.selector_range.raw_range,
            (0, 2),
        )


if __name__ == "__main__":
    unittest.main()
