import importlib
import unittest

# Preserve the application's normal import ordering.
from engine import Engine

from game.ability.factory import AbilityFactory


class UnitCannotDefendFactoryTests(unittest.TestCase):

    def test_attached_identity_can_block_defense_abilities(self):
        abilities = AbilityFactory.UnitCannotDefend(
            "AttachedIdentity",
            None,
            cannot_trigger_defense_ability=True,
        )

        self.assertEqual(len(abilities), 2)

    def test_wrapped_in_metal_script_builds_all_abilities(self):
        module = importlib.import_module(
            "cards.pack.mut_gen.magneto.32150",
        )

        self.assertEqual(len(module.GetAbilities()), 9)

    def test_shadowcat_obligation_uses_the_same_supported_selector(self):
        module = importlib.import_module(
            "cards.pack.mut_gen.shadowcat.32055",
        )

        self.assertEqual(len(module.GetAbilities()), 7)


if __name__ == "__main__":
    unittest.main()
