from types import SimpleNamespace
import unittest
from unittest.mock import Mock

# Preserve the application's normal import ordering.
from engine import Engine

from game.effect.effect_checker import EffectChecker
from game.effect.effect_failure import EffectFailure
from game.effect.effect_target_cost import TargetCost
from game.element.cost import Cost
from game.element.resources import Resources
from game.selector import Select
from game.selector.selector_rule import SelectorRule


class TargetInitiationContractTests(unittest.TestCase):

    def MakeTargetChecker(self, selector):
        player = Mock()
        effect = SimpleNamespace(
            ability=SimpleNamespace(
                selectors=[selector],
                flags=SimpleNamespace(
                    is_statistics=False,
                    is_delay_ability=False,
                ),
                is_label_attack=False,
                is_label_thwart=False,
            ),
            bind_message=None,
            context=SimpleNamespace(),
            initiator=player,
        )
        checker = EffectChecker.__new__(EffectChecker)
        checker.effect = effect
        checker.ability = effect.ability
        checker.failures = Mock()
        return checker, effect, player

    def test_optional_selector_remains_available_with_no_targets(self):
        selector = Mock()
        selector.condition = None
        selector.is_optional = True
        selector.target_text = None
        selector.GetAllLegalTargets.return_value = []
        selector.GetTargetRange.return_value = (0, 0)
        selector.selector_rule.select_rule = ""
        checker, effect, _ = self.MakeTargetChecker(selector)

        self.assertTrue(checker.UpdateLegalTargets())
        self.assertEqual(effect.context.target_range, (0, 0))
        self.assertEqual(effect.context.all_legal_targets, [])

    def test_mandatory_selector_blocks_initiation_with_no_targets(self):
        selector = Mock()
        selector.condition = None
        selector.is_optional = False
        selector.target_text = None
        selector.GetAllLegalTargets.return_value = []
        selector.GetTargetRange.return_value = None
        selector.selector_rule.select_rule = ""
        checker, _, _ = self.MakeTargetChecker(selector)

        self.assertFalse(checker.UpdateLegalTargets())

    def test_up_to_selector_accepts_zero_targets(self):
        selector = Select.From(faces=[Mock()], range=(0, 1))
        effect = SimpleNamespace(failures=Mock(), initiator=Mock())

        self.assertEqual(selector.GetTargetRange(effect, []), (0, 0))

    def test_target_that_left_play_is_rejected_before_cost_preparation(self):
        selector = Mock()
        selector.AfterSelectTargets.return_value = False
        target = Mock(name="target that left play")
        context = SimpleNamespace(
            targets_internal=[target],
            target_range=(1, 1),
            ignore_resource_cost=False,
            paid_this_resources=Resources("0"),
        )
        effect = SimpleNamespace(
            targets=[target],
            context=context,
            cost_func=SimpleNamespace(GetAll=lambda: []),
            PrepareSelfCosts=Mock(return_value=True),
            ValidatePreparedSelfCosts=Mock(return_value=True),
            ClearPreparedSelfCosts=Mock(),
        )
        checker = EffectChecker.__new__(EffectChecker)
        checker.effect = effect
        checker.ability = SimpleNamespace(selectors=[selector])
        checker.failures = Mock()
        checker.cost_for_different_target = TargetCost()
        player = Mock()

        self.assertFalse(checker.CheckBeforeActive(player))

        effect.PrepareSelfCosts.assert_not_called()
        player.SpendResource.assert_not_called()
        checker.failures.Set.assert_called_once_with(
            player,
            EffectFailure.CheckTarget,
        )

    def test_confirmed_target_selects_its_own_cost_and_payment(self):
        preview_target = Mock(name="preview target")
        confirmed_target = Mock(name="confirmed target")
        preview_resource = object()
        confirmed_resource = object()
        preview_payment = TargetCost.Payment(
            Cost("2"),
            [],
            [{preview_resource: "RR"}],
            {preview_resource: object()},
        )
        confirmed_payment = TargetCost.Payment(
            Cost("1"),
            [],
            [{confirmed_resource: "Y"}],
            {confirmed_resource: object()},
        )
        target_cost = TargetCost()
        target_cost.target_cost[preview_target] = preview_payment
        target_cost.target_cost[confirmed_target] = confirmed_payment
        selector = Mock()
        selector.AfterSelectTargets.return_value = True
        context = SimpleNamespace(
            targets_internal=[confirmed_target],
            target_range=(1, 1),
            ignore_resource_cost=False,
            paid_this_res_effects=[confirmed_resource],
            paid_this_cost=Cost("0"),
            paid_this_resources=Resources("0"),
            this_effect_need_cost=None,
        )
        effect = SimpleNamespace(
            targets=[confirmed_target],
            context=context,
            cost_func=SimpleNamespace(GetAll=lambda: []),
            PrepareSelfCosts=Mock(return_value=True),
            ValidatePreparedSelfCosts=Mock(return_value=True),
            ClearPreparedSelfCosts=Mock(),
        )
        checker = EffectChecker.__new__(EffectChecker)
        checker.effect = effect
        checker.ability = SimpleNamespace(selectors=[selector])
        checker.failures = Mock()
        checker.cost_for_different_target = target_cost
        player = Mock()
        player.SpendResource.return_value = Resources("Y")

        self.assertTrue(checker.CheckBeforeActive(player))

        player.SpendResource.assert_called_once_with(
            effect,
            [confirmed_resource],
            confirmed_payment,
        )

    def test_duplicate_and_excessive_target_assignments_are_rejected(self):
        first = Mock()
        first.card = Mock()
        second = Mock()
        second.card = Mock()
        effect = SimpleNamespace(failures=Mock())
        rule = SelectorRule()

        self.assertFalse(rule.AfterSelectTargets(effect, [first, first], (1, 2)))
        effect.failures.Set.assert_called_with(None, EffectFailure.DuplicateTarget)

        effect.failures.reset_mock()
        self.assertFalse(
            rule.AfterSelectTargets(effect, [first, second], (1, 1)),
        )
        effect.failures.Set.assert_called_with(None, EffectFailure.TargetNum)


if __name__ == "__main__":
    unittest.main()
