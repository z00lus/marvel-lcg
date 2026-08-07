import importlib.util
from pathlib import Path
import unittest


WORLD_RULE_FILE = Path(__file__).parents[1] / "game" / "world" / "world_rule.py"
WORLD_RULE_SPEC = importlib.util.spec_from_file_location("world_rule_under_test", WORLD_RULE_FILE)
assert WORLD_RULE_SPEC and WORLD_RULE_SPEC.loader
WORLD_RULE_MODULE = importlib.util.module_from_spec(WORLD_RULE_SPEC)
WORLD_RULE_SPEC.loader.exec_module(WORLD_RULE_MODULE)
WorldRule = WORLD_RULE_MODULE.WorldRule


class TestWorldRule(unittest.TestCase):
    def setUp(self) -> None:
        self.seed = 12345

    def Apply(self, rules):
        world_rule = WorldRule()
        world_rule.SetRule(rules, is_puzzle=False, seed=self.seed)
        return world_rule

    def test_rules_18_has_no_runtime_version_feature_flags(self):
        world_rule = self.Apply([])

        version_names = [
            var.name_true
            for var in world_rule.vars_bool
            if var.name_true.startswith(("v15_", "v16_", "v17_", "v18_"))
        ]
        self.assertEqual(version_names, [])

    def test_legacy_selectors_and_version_opt_outs_are_ignored(self):
        world_rule = self.Apply([
            "v16_all",
            "no_v16_teamwork",
            "no_v17_uniqueness",
            "no_v18_swaps",
        ])

        self.assertFalse(hasattr(world_rule, "v18_all"))
        self.assertFalse(hasattr(world_rule, "v16_teamwork"))
        self.assertFalse(hasattr(world_rule, "v17_uniqueness"))

    def test_non_version_game_options_remain_selectable(self):
        world_rule = self.Apply(["mode_campaign", "no_crisis_of_infinite_deadpools"])

        self.assertTrue(world_rule.mode_campaign)
        self.assertFalse(world_rule.crisis_of_infinite_deadpools)

    def test_recorded_rule_list_is_not_rewritten(self):
        recorded_rules = [
            "v18_all",
            "no_v18_surge",
            "mode_heroic_2",
            "encounter_cards_ignore_crisis",
        ]
        original_rules = recorded_rules[:]

        first = self.Apply(recorded_rules)
        second = self.Apply(recorded_rules)

        self.assertEqual(recorded_rules, original_rules)
        self.assertEqual(first.mode_heroic, 2)
        self.assertEqual(second.mode_heroic, 2)


if __name__ == '__main__':
    unittest.main()
