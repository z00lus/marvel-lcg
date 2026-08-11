import importlib
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

# Preserve the application's normal import ordering.
from engine import Engine

from game.card.face.card_type import Event, Identity
from game.effect.effect_checker import EffectChecker
from game.effect.effect_target_cost import TargetCost
from game.element.cost import Cost
from game.element.resources import Resources
from game.message import Message


class ResourcePaymentContractTests(unittest.TestCase):

    def test_generic_typed_wild_reduction_and_overpayment_matrix(self):
        rows = (
            ("generic exact", Resources("RB"), Cost("2"), True),
            ("generic insufficient", Resources("R"), Cost("2"), False),
            ("typed exact", Resources("Y"), Cost("Y"), True),
            ("typed wrong", Resources("R"), Cost("Y"), False),
            ("wild substitutes", Resources("G"), Cost("Y"), True),
            ("wild fills mixed requirement", Resources("YG"), Cost("YR"), True),
            ("discount combines with resource", Resources("R", reduce=1), Cost("2"), True),
            ("discount pays zero remainder", Resources("0", reduce=3), Cost("3"), True),
            ("overpayment", Resources("RRR"), Cost("2"), True),
        )

        for name, resources, cost, expected in rows:
            with self.subTest(name=name):
                self.assertEqual(resources.IsMatchCost(cost), expected)

    def test_payability_combines_distinct_resource_effects(self):
        first = object()
        second = object()
        target_cost = TargetCost()
        target_cost.SetNoneTargetOnly()
        target_cost.AddTarget(None, Cost("2"))
        target_cost.AddPayment(None, first, Resources("R"), object())
        target_cost.AddPayment(None, second, Resources("B"), object())

        self.assertTrue(target_cost.HasPayableTarget())
        selected = target_cost.GetResourcesForEffects(None, [first, second])
        self.assertIsNotNone(selected)
        self.assertTrue(selected.IsMatchCost(Cost("2")))

    def test_simultaneous_typed_components_require_a_valid_allocation(self):
        energy = object()
        physical = object()

        payable = TargetCost.Payment(
            Cost("YR"),
            [Cost("0", up_to=True), Cost("Y"), Cost("R")],
            [{energy: "Y"}, {physical: "R"}],
            {},
        )
        wrong_types = TargetCost.Payment(
            Cost("YR"),
            [Cost("0", up_to=True), Cost("Y"), Cost("R")],
            [{energy: "Y"}, {physical: "Y"}],
            {},
        )

        self.assertTrue(TargetCost.CanPay(payable))
        self.assertFalse(TargetCost.CanPay(wrong_types))

    def test_stale_target_payment_fails_without_spending(self):
        selected_target = object()
        stale_resource_effect = object()
        valid_resource_effect = object()
        payment = TargetCost.Payment(
            Cost("1"),
            [],
            [{valid_resource_effect: "R"}],
            {valid_resource_effect: object()},
        )
        target_cost = TargetCost()
        target_cost.target_cost[selected_target] = payment
        context = SimpleNamespace(
            ignore_resource_cost=False,
            paid_this_res_effects=[stale_resource_effect],
            paid_this_cost=Cost("0"),
            paid_this_resources=Resources("0"),
            this_effect_need_cost=None,
            targets_internal=[selected_target],
        )
        effect = SimpleNamespace(
            targets=[selected_target],
            context=context,
            cost_func=SimpleNamespace(GetAll=lambda: []),
            PrepareSelfCosts=Mock(return_value=True),
            ValidatePreparedSelfCosts=Mock(return_value=True),
            ClearPreparedSelfCosts=Mock(),
        )
        checker = EffectChecker.__new__(EffectChecker)
        checker.effect = effect
        checker.ability = SimpleNamespace(selectors=[])
        checker.cost_for_different_target = target_cost
        checker.failures = Mock()
        player = Mock()

        self.assertFalse(checker.CheckBeforeActive(player))

        effect.ClearPreparedSelfCosts.assert_called_once()
        player.SpendResource.assert_not_called()
        player.res_pool.Reset.assert_not_called()

    def test_star_lord_discount_is_scoped_to_the_played_card_not_its_target(self):
        star_lord = importlib.import_module(
            "cards.pack.stld.star_lord.17001a",
        )
        ability = star_lord.GetAbilities()[-1]
        player = Mock(name="Star-Lord player")
        source = Mock(name="Star-Lord identity")
        source.IsInPlay.return_value = True
        source.GetControlBy.return_value = player
        source.effect.Find.return_value = [Mock(name="discount payment")]
        played_card = Mock(name="Sliding Shot")
        played_card.IsLikeInHand.return_value = True
        played_card.GetAttachedUpgrades.return_value = []
        villain = Mock(name="Ronan")

        target_cost = TargetCost()
        target_cost.SetNoneTargetOnly()
        target_cost.AddTarget(None, Cost("4"))
        paying_effect = SimpleNamespace(
            this=played_card,
            ability=SimpleNamespace(is_play=True, name="Play"),
            checker=SimpleNamespace(cost_for_different_target=target_cost),
        )
        message = SimpleNamespace(
            paying_for_effect=paying_effect,
            paying_for_targets=[villain],
            paying_for_target=villain,
            paying_for_card=played_card,
            cost=Cost("4"),
            GetToPlayer=lambda: player,
            AddPayment=Mock(),
        )
        effect = SimpleNamespace(
            this=source,
            ability=ability,
            initiator=player,
            context=SimpleNamespace(initiator=player),
            GetInitiator=lambda: player,
            checker=SimpleNamespace(HasCostTargets=lambda: True),
            world=SimpleNamespace(
                stat=SimpleNamespace(IsOncePerRound=lambda _: True),
            ),
        )

        with patch.object(Identity, "IsType", return_value=True), \
             patch.object(Event, "IsType", return_value=False):
            self.assertTrue(all(
                condition(effect, message)
                for condition in ability.conditions
            ))

            generated = SimpleNamespace(
                res=Resources("0", reduce=3),
                Send=Mock(),
            )
            with patch.object(
                Message,
                "CheckEffectGeneratedResources",
                return_value=generated,
            ):
                ability.operation(effect, message)

        message.AddPayment.assert_called_once()
        _, discount, check_effect = message.AddPayment.call_args.args
        self.assertEqual(discount.reduce, 3)
        self.assertIs(check_effect, effect)

        played_card.IsLikeInHand.return_value = False
        with patch.object(Identity, "IsType", return_value=True), \
             patch.object(Event, "IsType", return_value=False):
            self.assertFalse(all(
                condition(effect, message)
                for condition in ability.conditions
            ))


if __name__ == "__main__":
    unittest.main()
