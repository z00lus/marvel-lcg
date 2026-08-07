from pathlib import Path
import unittest

from build import Build
from engine.lib.version import Ver


ROOT = Path(__file__).resolve().parents[1]


class V18SetupUiTests(unittest.TestCase):

    def test_ronin_edition_release_identity_is_consistent(self):
        Ver.Initialize()

        self.assertEqual(
            Build.PRODUCT_NAME,
            'Marvel Champions Digital: Ronin Edition',
        )
        self.assertEqual(Build.RELEASE_VERSION, '0.6.0')
        self.assertEqual(Build.RELEASE_CODENAME, 'Echo')
        self.assertEqual(str(Ver.version), '0.6.0.0')
        self.assertEqual(Ver.ui_version_str, '0.6.0.0r')
        self.assertEqual(Ver.release_label, 'Version 0.6.0 — “Echo”')

    def test_start_page_displays_ronin_edition_and_echo_release(self):
        source = (ROOT / 'public/main.html').read_text(encoding='utf-8')

        self.assertIn('Marvel Champions Digital: Ronin Edition', source)
        self.assertIn('<h1>Marvel Champions Digital</h1>', source)
        self.assertIn('<h2>Ronin Edition</h2>', source)
        self.assertIn('Version 0.6.0 — “Echo”', source)
        self.assertIn('Based on', source)
        self.assertIn('Marvel Champions: Digital Edition', source)
        self.assertIn('by Irefrixs', source)

    def test_quick_game_uses_only_v18_rules(self):
        source = (ROOT / "public/js/solo.ts").read_text(encoding="utf-8")

        self.assertIn("rules: ['v18_all']", source)
        self.assertNotIn("v16_all", source)
        self.assertNotIn("encounter_cards_ignore_crisis", source)

    def test_campaign_uses_v18_campaign_rules(self):
        source = (ROOT / "public/js/campaign.ts").read_text(encoding="utf-8")

        self.assertIn("'mode_campaign'", source)
        self.assertIn("'v18_all'", source)
        self.assertNotIn("v16_all", source)
        self.assertNotIn("encounter_cards_ignore_crisis", source)

    def test_advanced_setup_has_no_rules_compatibility_controls(self):
        source = (ROOT / "public/scene.html").read_text(encoding="utf-8")

        self.assertIn("new_game.rules.push('v18_all')", source)
        self.assertNotIn('id="rules"', source)
        self.assertNotIn("new_game.rules.push('no_encounter_cards_ignore_crisis')", source)
        self.assertNotIn("new_game.rules.push('no_crisis_of_infinite_deadpools')", source)


if __name__ == "__main__":
    unittest.main()
