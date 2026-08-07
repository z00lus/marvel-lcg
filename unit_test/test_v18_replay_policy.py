import unittest

# Preserve the application's normal import ordering.
from engine import Engine

from game.scene.loader import (
    LoaderHelper,
    UnsupportedReplayRulesError,
)
from game.scene.scene import Scene


class V18ReplayPolicyTests(unittest.TestCase):

    def test_legacy_replay_is_rejected_with_a_clear_error(self):
        scene = Scene(rules=['v16_all'])

        with self.assertRaisesRegex(
            UnsupportedReplayRulesError,
            'legacy rules.*not compatible',
        ):
            LoaderHelper.EnsureSupportedReplay(scene)

    def test_v18_replay_is_accepted(self):
        LoaderHelper.EnsureSupportedReplay(Scene(rules=['v18_all']))

    def test_new_game_rules_are_normalized_to_v18(self):
        rules = LoaderHelper.NormalizeV18Rules([
            'mode_campaign',
            'v16_all',
            'no_v18_timing',
            'no_fix_surge',
            'no_crisis_of_infinite_deadpools',
        ])

        self.assertEqual(
            rules,
            [
                'mode_campaign',
                'v18_all',
            ],
        )

    def test_new_game_discards_obsolete_crisis_compatibility_flags(self):
        rules = LoaderHelper.NormalizeV18Rules([
            'encounter_cards_ignore_crisis',
            'no_encounter_cards_ignore_crisis',
            'crisis_of_infinite_deadpools',
            'no_crisis_of_infinite_deadpools',
        ])

        self.assertEqual(rules, ['v18_all'])


if __name__ == '__main__':
    unittest.main()
