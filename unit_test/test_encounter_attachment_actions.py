import importlib
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

# Preserve the application's normal import ordering.
from engine import Engine

from game.ability.ability_type import AbilityType
from game.card.face.card_type import Attachment, Identity
from game.event.manager import EventManager


class EncounterAttachmentActionTests(unittest.TestCase):

    def GetCardAction(self, module_name: str, ability_type: AbilityType):
        module = importlib.import_module(module_name)
        actions = [
            ability for ability in module.GetAbilities()
            if ability.type == ability_type
        ]
        self.assertEqual(len(actions), 1)
        return actions[0]

    def MakeIdentityAttachmentEffect(self, ability, scenario_owner):
        identity = SimpleNamespace()
        area = SimpleNamespace(
            flags=SimpleNamespace(is_removed=False),
            GetOwner=lambda: scenario_owner,
        )
        attachment = SimpleNamespace(
            bind_face=identity,
            card=SimpleNamespace(area=area),
            is_treat_as_if_blank=False,
            IsInPlay=lambda: True,
            GetControlByOrOwner=lambda: scenario_owner,
        )
        effect = SimpleNamespace(
            ability=ability,
            failures=Mock(),
            is_forced=False,
            is_unregister=False,
            this=attachment,
        )
        return identity, attachment, effect

    def FilterAction(self, ability, asked_player, current_player):
        scenario_owner = SimpleNamespace(name="Scenario")
        identity, attachment, effect = self.MakeIdentityAttachmentEffect(
            ability,
            scenario_owner,
        )
        message = object.__new__(ability.when)
        world = SimpleNamespace(GetCurrentPlayer=lambda: current_player)

        with patch.object(
            Attachment,
            "IsType",
            side_effect=lambda face: face is attachment,
        ), patch.object(
            Identity,
            "IsType",
            side_effect=lambda face: face is identity,
        ):
            available = EventManager.SimpleCheckEffects(
                message,
                [effect],
                asked_player,
                world,
                None,
            )

        return effect, available

    def test_restrained_hero_action_is_available_to_active_player(self):
        ability = self.GetCardAction(
            "cards.pack.mts.ebony_maw.21083",
            AbilityType.HeroAction,
        )
        player = SimpleNamespace(name="Spectrum")

        effect, available = self.FilterAction(ability, player, player)

        self.assertEqual(available, [effect])
        cost = ability.GetCost(effect, [])
        self.assertEqual((cost.y, cost.r, cost.b, cost.g), (1, 1, 0, 0))

    def test_seduced_alter_ego_action_is_available_to_active_player(self):
        ability = self.GetCardAction(
            "cards.pack.mts.enchantress.21179",
            AbilityType.AlterEgoAction,
        )
        player = SimpleNamespace(name="Player")

        effect, available = self.FilterAction(ability, player, player)

        self.assertEqual(available, [effect])
        cost = ability.GetCost(effect, [])
        self.assertEqual((cost.y, cost.r, cost.b, cost.g), (1, 0, 1, 0))

    def test_identity_attachment_action_is_not_offered_to_inactive_player(self):
        ability = self.GetCardAction(
            "cards.pack.mts.ebony_maw.21083",
            AbilityType.HeroAction,
        )
        active_player = SimpleNamespace(name="Active")
        inactive_player = SimpleNamespace(name="Inactive")

        effect, available = self.FilterAction(
            ability,
            inactive_player,
            active_player,
        )

        self.assertEqual(available, [])
        effect.failures.SetText.assert_called_once()


if __name__ == "__main__":
    unittest.main()
