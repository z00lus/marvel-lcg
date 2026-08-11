import importlib
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

# Preserve the application's normal import ordering.
from engine import Engine

from game.ability.ability_type import AbilityType
from game.card.face.card_type import Attachment, Identity
from game.effect.effect_checker import EffectChecker
from game.effect.effect_target_cost import TargetCost
from game.element.cost import Cost
from game.element.resources import Resources
from game.event.manager import EventManager
from game.operate.faces import Faces


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

    def AssertTypedPaymentDiscardsAttachment(
        self,
        module_name: str,
        ability_type: AbilityType,
        resources: str,
        expected_cost: str,
    ):
        ability = self.GetCardAction(module_name, ability_type)
        payment_effect = object()
        target_cost = TargetCost()
        target_cost.SetNoneTargetOnly()
        target_cost.AddTarget(None, Cost(expected_cost))
        target_cost.AddPayment(
            None,
            payment_effect,
            Resources(resources),
            object(),
        )
        attachment = Mock(name=module_name)
        context = SimpleNamespace(
            ignore_resource_cost=False,
            paid_this_res_effects=[payment_effect],
            paid_this_cost=Cost("0"),
            paid_this_resources=Resources("0"),
            this_effect_need_cost=None,
            targets_internal=[],
            target_range=(0, 0),
        )
        effect = SimpleNamespace(
            this=attachment,
            ability=ability,
            targets=[],
            context=context,
            cost_func=SimpleNamespace(GetAll=lambda: []),
            PrepareSelfCosts=Mock(return_value=True),
            ValidatePreparedSelfCosts=Mock(return_value=True),
            ClearPreparedSelfCosts=Mock(),
        )
        checker = EffectChecker.__new__(EffectChecker)
        checker.effect = effect
        checker.ability = ability
        checker.cost_for_different_target = target_cost
        checker.failures = Mock()
        player = Mock()
        player.SpendResource.return_value = Resources(resources)

        self.assertTrue(checker.CheckBeforeActive(player))
        player.SpendResource.assert_called_once()

        with patch.object(Faces, "DiscardAll", return_value=[attachment]) as discard:
            ability.operation(effect, Mock())

        discard.assert_called_once_with([attachment], effect)

    def test_restrained_pays_energy_physical_then_discards_itself(self):
        self.AssertTypedPaymentDiscardsAttachment(
            "cards.pack.mts.ebony_maw.21083",
            AbilityType.HeroAction,
            "YR",
            "YR",
        )

    def test_seduced_pays_energy_mental_then_discards_itself(self):
        self.AssertTypedPaymentDiscardsAttachment(
            "cards.pack.mts.enchantress.21179",
            AbilityType.AlterEgoAction,
            "YB",
            "YB",
        )


if __name__ == "__main__":
    unittest.main()
