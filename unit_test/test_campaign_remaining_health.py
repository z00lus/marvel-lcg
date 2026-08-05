from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from engine import Engine  # noqa: F401 - establishes the project's import order
from game.ability.factory.campaign import AbilityFactoryCampaign
from game.message import Message


class TestCampaignRemainingHealth(unittest.TestCase):

    def test_remaining_health_is_applied_during_campaign_setup(self):
        ability = AbilityFactoryCampaign.CampaignSetPlayersHPToTheirRemainingHP(
            campaign_id="agents_of_shield",
        )
        identity = MagicMock()
        player = SimpleNamespace(
            player_id=0,
            GetIdentity=MagicMock(return_value=identity),
        )
        effect = SimpleNamespace()

        with patch(
            "game.operate.worlds.Worlds.GetPlayers",
            return_value=[player],
        ), patch(
            "game.operate.campaign_logs.CampaignLog.GetIntByPlayer",
            return_value=4,
        ):
            ability.operation(effect, SimpleNamespace())

        self.assertIs(ability.when, Message.WhenCampaignSetup)
        identity.SetHealth.assert_called_once_with(4, effect)

    def test_remaining_health_is_not_expert_only(self):
        ability = AbilityFactoryCampaign.CampaignSetPlayersHPToTheirRemainingHP(
            campaign_id="agents_of_shield",
        )
        effect = SimpleNamespace()
        message = SimpleNamespace()

        with patch(
            "game.operate.worlds.Worlds.IsCampaign",
            return_value=True,
        ), patch(
            "game.operate.worlds.Worlds.IsCampaignSelected",
            return_value=True,
        ), patch(
            "game.operate.worlds.Worlds.IsExpert",
            side_effect=AssertionError("standard setup must not check expert mode"),
        ):
            self.assertTrue(ability.conditions[0](effect, message))


if __name__ == "__main__":
    unittest.main()
