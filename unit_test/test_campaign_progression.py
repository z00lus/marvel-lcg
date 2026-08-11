import json
from importlib import import_module
from pathlib import Path
import re
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from engine import Engine  # noqa: F401 - establishes the project's import order
from engine.lib.version import Ver
from cards.pack.aos.campaign import (
    ResolveEarnedEvidenceSetup,
    _campaign_flag,
    _campaign_int,
    _campaign_list,
)
from game.operate.campaign_logs import CampaignLog
from game.game_run.campaign_progress import CAMPAIGN_SCENARIOS
from game.scene.loader import SceneLoader
from game.world.variable import Variable


ROOT = Path(__file__).resolve().parents[1]

EXPECTED_CAMPAIGNS = {
    "rise_of_red_skull": [
        "crossbones", "absorbing_man", "taskmaster", "zola", "red_skull",
    ],
    "galaxys_most_wanted": [
        "brotherhood_of_badoon", "infiltrate_the_museum",
        "escape_the_museum", "nebula", "ronan",
    ],
    "mad_titans_shadow": [
        "ebony_maw", "the_tower_defense", "thanos", "hela", "loki",
    ],
    "sinister_motives": [
        "sandman", "venom", "mysterio", "sinister_six", "venom_goblin",
    ],
    "mutant_genesis": [
        "sabretooth", "project_wideawake", "master_mold",
        "mansion_attack", "magneto",
    ],
    "next_evolution": [
        "morlock_siege", "on_the_run", "juggernaut", "mister_sinister",
        "stryfe",
    ],
    "age_of_apocalypse": [
        "unus", "four_horsemen", "apocalypse", "dark_beast",
        "en_sabah_nur",
    ],
    "agents_of_shield": [
        "black_widow", "batroc", "modok", "thunderbolts", "baron_zemo",
    ],
}


class TestCampaignProgression(unittest.TestCase):

    def test_simplified_ui_campaigns_have_five_scenarios_in_expected_order(self):
        source = (ROOT / "public" / "js" / "campaign_state.ts").read_text(
            encoding="utf-8"
        )
        definitions = {}
        for campaign_id, scenario_source in re.findall(
            r"id:\s*'([^']+)'.*?scenarios:\s*\[([^\]]+)\]",
            source,
            flags=re.DOTALL,
        ):
            definitions[campaign_id] = re.findall(r"'([^']+)'", scenario_source)

        self.assertEqual(definitions, EXPECTED_CAMPAIGNS)
        self.assertEqual(CAMPAIGN_SCENARIOS, EXPECTED_CAMPAIGNS)
        scenario_folder = ROOT / "data" / "scenarios"
        for campaign_id, scenarios in definitions.items():
            with self.subTest(campaign=campaign_id):
                self.assertEqual(len(scenarios), 5)
                for scenario in scenarios:
                    self.assertTrue((scenario_folder / f"{scenario}.json").is_file())
                    self.assertTrue(
                        (scenario_folder / f"{scenario}_expert.json").is_file()
                    )

    def test_exported_campaign_log_round_trips_into_the_next_scene(self):
        previous_store = Variable()
        previous_store.SetStr("Evidence Seed", "74321")
        previous_store.SetStr("Evidence Earned", "50185;50189")
        previous_store.SetStr("Chief Medical Officer Flipped", "Yes")
        previous_store.SetStr(
            "Scenario 1 Chief Medical Officer Secret Counters",
            "2",
        )
        identity = SimpleNamespace(health=5)
        player = SimpleNamespace(
            player_id=0,
            GetIdentity=lambda: identity,
        )
        previous_world = SimpleNamespace(
            store=previous_store,
            const_players=[player],
        )
        exported = CampaignLog.Export(
            previous_world,
            include_remaining_hit_points=True,
        )

        campaign = {
            "version": "0.6.0",
            "campaign_id": "agents_of_shield",
            "name": "Batroc",
            "villain": ["50086a"],
            "expert": False,
            "schemes": ["50087a,50087b"],
            "set_aside": [],
            "encounters": [],
            "encounter_sets": ["standard"],
            "modular_sets": ["aim_science", "batrocs_brigade"],
            "campaign_log": {},
        }
        hero = {
            "version": "0.6.0",
            "name": "Spider-Man",
            "hero": ["01001a,01001b"],
            "hero_deck": [],
            "obligations": [],
            "nemesis_set": [],
            "player_deck": [],
        }
        Ver.Initialize()
        scene = SceneLoader.NewFromJson(
            json.dumps(campaign),
            ["standard", "aim_science", "batrocs_brigade"],
            [json.dumps(hero)],
            123,
            ["mode_campaign", "v18_all"],
            exported,
        )

        next_store = Variable()
        for key, value in scene.campaign.campaign_log.items():
            next_store.SetStr(key, value)
        effect = SimpleNamespace(world=SimpleNamespace(store=next_store))

        self.assertEqual(_campaign_int("Evidence Seed", effect), 74321)
        self.assertEqual(
            _campaign_list("Evidence Earned", effect),
            ["50185", "50189"],
        )
        self.assertTrue(_campaign_flag("Chief Medical Officer Flipped", effect))
        self.assertEqual(
            _campaign_int(
                "Scenario 1 Chief Medical Officer Secret Counters",
                effect,
            ),
            2,
        )
        self.assertEqual(
            scene.campaign.campaign_log["Player 1 Remaining hit points"],
            "5",
        )

    def test_earned_evidence_from_export_resolves_in_next_scenario(self):
        evidence = MagicMock()
        removed = MagicMock()
        removed.FindCard.side_effect = lambda *, card_ids: (
            evidence if card_ids == ["50185"] else None
        )
        store = Variable()
        store.SetStr("Evidence Earned", "50185")
        effect = SimpleNamespace(
            world=SimpleNamespace(store=store, area_removed=removed),
        )

        with patch(
            "cards.pack.aos.campaign.Evidence.IsType",
            return_value=True,
        ):
            ResolveEarnedEvidenceSetup().operation(effect, SimpleNamespace())

        evidence.Setup.assert_called_once_with(False)

    def test_affected_campaign_card_modules_import_and_build_abilities(self):
        modules = [
            "cards.pack.aos.shield_executive_board.50181a",
            "cards.pack.aos.shield_executive_board.50181b",
            "cards.pack.aos.shield_executive_board.50182a",
            "cards.pack.aos.shield_executive_board.50182b",
            "cards.pack.aos.shield_executive_board.50183a",
            "cards.pack.aos.shield_executive_board.50183b",
        ] + [
            f"cards.pack.aos.executive_board_evidence.{card_id}"
            for card_id in range(50185, 50194)
        ]

        for module_name in modules:
            with self.subTest(module=module_name):
                abilities = import_module(module_name).GetAbilities()
                self.assertTrue(abilities)


if __name__ == "__main__":
    unittest.main()
