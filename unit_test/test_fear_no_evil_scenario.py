from __future__ import annotations

import importlib
import json
from pathlib import Path
import unittest
from unittest.mock import ANY, Mock, patch

# Match the application's import order without initializing the server.
from engine import Engine  # noqa: F401
from build import Build
from cards.database import CardsDB
from engine.lib.json import Json
from engine.lib.version import Ver
from game.card.factory import CardFactory
from game.card.face.attribute.can_boost import CanBoost
from game.message import Message
from game.operate.faces import Faces
from game.operate.worlds import Worlds
from game.scene.loader import SceneLoader
from game.world.phase import Phase
from game.world.world import World


ROOT = Path(__file__).resolve().parents[1]
UNDERLING_IDS = [
    "bullseye",
    "electro",
    "hammerhead",
    "purple_man",
    "typhoid_mary",
]
CARD_IDS = [
    "60065", "60066", "60067", "60068a", "60068b",
    *[str(card_id) for card_id in range(60069, 60076)],
    *[str(card_id) for card_id in range(60076, 60086)],
    *[str(card_id) for card_id in range(60086, 60097)],
    *[str(card_id) for card_id in range(60097, 60110)],
    "60110a", "60110b", "60111a", "60111b", "60112", "60113a", "60113b",
    *[str(card_id) for card_id in range(60114, 60121)],
    "60128a", "60128b", "60129a", "60129b",
    *[str(card_id) for card_id in range(60130, 60134)],
    *[str(card_id) for card_id in range(60182, 60191)],
    "60121a", "60121b",
    *[str(card_id) for card_id in range(60122, 60128)],
    *[str(card_id) for card_id in range(60191, 60195)],
    "60142a", "60142b",
    *[str(card_id) for card_id in range(60143, 60151)],
    *[str(card_id) for card_id in range(60195, 60200)],
    *[f"6013{value}{face}" for value in range(4, 9) for face in ("a", "b")],
    *[str(card_id) for card_id in range(60139, 60142)],
    *[str(card_id) for card_id in range(60177, 60182)],
    *[str(card_id) for card_id in range(60200, 60205)],
    "60159a", "60159b", "60160a", "60160b",
    "60161a", "60161b", "60162a", "60162b", "60163a", "60163b",
    *[str(card_id) for card_id in range(60164, 60177)],
]
SCRIPT_MODULES = [
    *(f"cards.pack.fne.bullseye.{card_id}" for card_id in (
        "60065", "60066", "60067", "60068a", "60068b",
        *[str(value) for value in range(60069, 60076)],
    )),
    *(f"cards.pack.fne.electro.{card_id}" for card_id in range(60076, 60086)),
    *(f"cards.pack.fne.hammerhead.{card_id}" for card_id in range(60086, 60097)),
    *(f"cards.pack.fne.purple_man.{card_id}" for card_id in range(60097, 60110)),
    *(f"cards.pack.fne.typhoid_mary.{card_id}" for card_id in (
        "60110a", "60110b", "60111a", "60111b", "60112", "60113a", "60113b",
        *[str(value) for value in range(60114, 60121)],
    )),
    *(f"cards.pack.fne.the_getaway.{card_id}" for card_id in (
        "60128a", "60128b", "60129a", "60129b",
        *[str(value) for value in range(60130, 60134)],
    )),
    *(f"cards.pack.fne.cops.{card_id}" for card_id in range(60182, 60186)),
    *(f"cards.pack.fne.drive.{card_id}" for card_id in range(60186, 60191)),
    *(f"cards.pack.fne.art_museum_heist.{card_id}" for card_id in (
        "60121a", "60121b", *[str(value) for value in range(60122, 60128)],
    )),
    *(f"cards.pack.fne.the_owl.{card_id}" for card_id in range(60191, 60195)),
    *(f"cards.pack.fne.the_raft_breakout.{card_id}" for card_id in (
        "60142a", "60142b", *[str(value) for value in range(60143, 60151)],
    )),
    *(f"cards.pack.fne.tombstone.{card_id}" for card_id in range(60195, 60200)),
    *(f"cards.pack.fne.protection_racket.6013{value}{face}"
      for value in range(4, 9) for face in ("a", "b")),
    *(f"cards.pack.fne.protection_racket.{card_id}" for card_id in range(60139, 60142)),
    *(f"cards.pack.fne.disasters.{card_id}" for card_id in range(60177, 60182)),
    *(f"cards.pack.fne.tracksuit_mafia.{card_id}" for card_id in range(60200, 60205)),
    *(f"cards.pack.fne.kingpin.{card_id}" for card_id in (
        "60159a", "60159b", "60160a", "60160b",
        "60161a", "60161b", "60162a", "60162b", "60163a", "60163b",
        *[str(value) for value in range(60164, 60177)],
    )),
]


class FearNoEvilStructureTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        Ver.Initialize()
        if not CardsDB.papers:
            CardsDB.Initialize()

    def initialize_world(self, scenario: dict, seed: int) -> World:
        hero_json = (ROOT / "deck/starter/spider_man.json").read_text(
            encoding="utf-8"
        )
        scene = SceneLoader.NewFromJson(
            json.dumps(scenario),
            scenario["encounter_sets"] + scenario["modular_sets"],
            [hero_json],
            seed,
            [
                "v18_all",
                "disable_setup_draw_cards",
                "disable_resolve_mulligans",
            ],
            {},
        )
        with patch.object(Build, "release", False):
            manager = Mock()
            manager.skip.is_skipping = True
            manager.undo.GetFastUndoHandle.return_value = None
            controller = Mock(manager=manager)
            world = World(scene, [controller])
            world.rule.SetRule(scene.rules, scene.is_puzzle, scene.seed)
            world.insert = CardFactory.GenerateCard(
                "rule_a,rule_b",
                world.area_insert,
                world,
                ui_render=False,
            ).face

            statistics = Mock()
            statistics.CanRegisterAbility.return_value = False
            game = Mock()
            game.controller_manager = manager
            game.state.is_running = True
            game.session.version.IsFirstPlayerToken.return_value = True
            with (
                patch.object(Engine, "game", game, create=True),
                patch.object(Engine, "statistics", statistics, create=True),
            ):
                world.Initialize()
        return world

    def test_data_checksums_are_current(self):
        for path in (ROOT / "data/cards.json", ROOT / "data/sets_info.json"):
            with self.subTest(path=path.name):
                _, checksum = Json.LoadInternal(str(path))
                self.assertEqual(checksum, "Ok")

    def test_the_getaway_uses_selected_underling_and_required_sets(self):
        for expert in (False, True):
            suffix = "_expert" if expert else ""
            path = ROOT / f"data/scenarios/the_getaway{suffix}.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            with self.subTest(expert=expert):
                self.assertEqual(data["name"], "The Getaway")
                self.assertEqual(
                    data["underling_sets"],
                    UNDERLING_IDS,
                )
                self.assertEqual(data["modular_sets"], ["cops", "drive"])
                self.assertEqual(data["expert"], expert)
                self.assertEqual(data["villain"], ["60066", "60067"] if expert else ["60065", "60066"])

    def test_bullseye_underling_data_supplies_both_difficulties(self):
        sets_info = json.loads(
            (ROOT / "data/sets_info.json").read_text(encoding="utf-8")
        )["60. Fear No Evil"]
        self.assertEqual(
            sets_info["underlings"],
            UNDERLING_IDS,
        )
        self.assertNotIn("bullseye", sets_info["encounters"])

        data = json.loads(
            (ROOT / "data/encounter_sets/bullseye.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(data["villain"], ["60065", "60066"])
        self.assertEqual(data["expert_villain"], ["60066", "60067"])
        self.assertEqual(data["set_aside"], ["60068a,60068b"])
        self.assertEqual(len(data["encounters"]), 10)

    def test_electro_underling_data_supplies_both_difficulties(self):
        data = json.loads(
            (ROOT / "data/encounter_sets/electro.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(data["villain"], ["60076", "60077"])
        self.assertEqual(data["expert_villain"], ["60077", "60078"])
        self.assertEqual(data["set_aside"], ["60079"])
        self.assertEqual(len(data["encounters"]), 10)
        self.assertEqual(data["encounters"].count("60081"), 1)
        for duplicated_id in ("60082", "60083", "60084", "60085"):
            self.assertEqual(data["encounters"].count(duplicated_id), 2)

    def test_purple_man_underling_data_supplies_both_difficulties(self):
        data = json.loads(
            (ROOT / "data/encounter_sets/purple_man.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(data["villain"], ["60097", "60098"])
        self.assertEqual(data["expert_villain"], ["60098", "60099"])
        self.assertEqual(data["set_aside"], [])
        self.assertEqual(len(data["encounters"]), 12)
        self.assertEqual(data["encounters"].count("60101"), 2)
        self.assertEqual(data["encounters"].count("60109"), 2)

    def test_hammerhead_underling_data_supplies_both_difficulties(self):
        data = json.loads(
            (ROOT / "data/encounter_sets/hammerhead.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(data["villain"], ["60086", "60087"])
        self.assertEqual(data["expert_villain"], ["60087", "60088"])
        self.assertEqual(data["set_aside"], [])
        self.assertEqual(len(data["encounters"]), 11)
        for duplicated_id in ("60092", "60093", "60096"):
            self.assertEqual(data["encounters"].count(duplicated_id), 2)

    def test_typhoid_mary_underling_data_supplies_both_difficulties(self):
        data = json.loads(
            (ROOT / "data/encounter_sets/typhoid_mary.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(data["villain"], ["60110a,60110b"])
        self.assertEqual(data["expert_villain"], ["60111a,60111b"])
        self.assertEqual(data["set_aside"], [])
        self.assertEqual(len(data["encounters"]), 13)
        self.assertEqual(data["encounters"].count("60115"), 2)
        self.assertEqual(data["encounters"].count("60118"), 2)
        self.assertEqual(data["encounters"].count("60120"), 3)

    def test_all_mix_and_match_scenarios_offer_every_underling(self):
        for scenario_id in (
            "the_getaway",
            "art_museum_heist",
            "the_raft_breakout",
            "protection_racket",
            "stop_the_presses",
        ):
            for expert in (False, True):
                suffix = "_expert" if expert else ""
                data = json.loads(
                    (ROOT / f"data/scenarios/{scenario_id}{suffix}.json").read_text(
                        encoding="utf-8"
                    )
                )
                with self.subTest(scenario=scenario_id, expert=expert):
                    self.assertEqual(data["underling_sets"], UNDERLING_IDS)

    def test_kingpin_scenario_uses_fixed_stage_pairs_and_required_sets(self):
        sets_info = json.loads(
            (ROOT / "data/sets_info.json").read_text(encoding="utf-8")
        )["60. Fear No Evil"]
        self.assertIn("kingpin", sets_info["scenarios"])

        for expert in (False, True):
            suffix = "_expert" if expert else ""
            data = json.loads(
                (ROOT / f"data/scenarios/kingpin{suffix}.json").read_text(
                    encoding="utf-8"
                )
            )
            with self.subTest(expert=expert):
                self.assertEqual(data["name"], "Kingpin")
                self.assertEqual(data["expert"], expert)
                self.assertEqual(
                    data["villain"],
                    ["60160a,60160b"] if expert else ["60159a,60159b"],
                )
                self.assertEqual(
                    data["schemes"],
                    ["60161a,60161b", "60162a,60162b"],
                )
                self.assertEqual(data["set_aside"], ["60163a,60163b"])
                self.assertEqual(data["encounter_sets"], [])
                self.assertEqual(
                    data["modular_sets"],
                    ["tombstone", "tracksuit_mafia"],
                )
                self.assertEqual(len(data["encounters"]), 17)

    def test_quick_game_payload_builds_a_complete_getaway_scene(self):
        scenario = json.loads(
            (ROOT / "data/scenarios/the_getaway.json").read_text(
                encoding="utf-8"
            )
        )
        underling = json.loads(
            (ROOT / "data/encounter_sets/bullseye.json").read_text(
                encoding="utf-8"
            )
        )
        scenario["villain"] = underling["villain"]
        scenario["set_aside"] += underling["set_aside"]
        scenario["encounters"] += underling["encounters"]

        scene = SceneLoader.NewFromJson(
            json.dumps(scenario),
            scenario["encounter_sets"] + scenario["modular_sets"],
            [],
            1,
            ["v18_all"],
            {},
        )

        self.assertEqual(scene.campaign.villain, ["60065", "60066"])
        self.assertEqual(
            scene.campaign.set_aside,
            ["60129a,60129b", "60068a,60068b"],
        )
        self.assertEqual(len(scene.campaign.encounters), 16)
        self.assertEqual(
            scene.campaign.encounter_sets,
            ["standard", "cops", "drive"],
        )

    def test_electro_reaches_first_player_turn_on_standard_and_expert(self):
        hero_json = (ROOT / "deck/starter/spider_man.json").read_text(
            encoding="utf-8"
        )

        for expert in (False, True):
            with self.subTest(expert=expert):
                suffix = "_expert" if expert else ""
                scenario = json.loads(
                    (ROOT / f"data/scenarios/the_getaway{suffix}.json").read_text(
                        encoding="utf-8"
                    )
                )
                underling = json.loads(
                    (ROOT / "data/encounter_sets/electro.json").read_text(
                        encoding="utf-8"
                    )
                )
                scenario["villain"] = underling[
                    "expert_villain" if expert else "villain"
                ]
                scenario["set_aside"] += underling["set_aside"]
                scenario["encounters"] += underling["encounters"]

                scene = SceneLoader.NewFromJson(
                    json.dumps(scenario),
                    scenario["encounter_sets"] + scenario["modular_sets"],
                    [hero_json],
                    60079,
                    [
                        "v18_all",
                        "disable_setup_draw_cards",
                        "disable_resolve_mulligans",
                    ],
                    {},
                )
                manager = Mock()
                manager.skip.is_skipping = True
                manager.undo.GetFastUndoHandle.return_value = None
                controller = Mock(manager=manager)
                world = World(scene, [controller])
                world.rule.SetRule(scene.rules, scene.is_puzzle, scene.seed)
                world.insert = CardFactory.GenerateCard(
                    "rule_a,rule_b",
                    world.area_insert,
                    world,
                    ui_render=False,
                ).face

                statistics = Mock()
                statistics.CanRegisterAbility.return_value = False
                game = Mock()
                game.controller_manager = manager
                game.state.is_running = True
                game.session.version.IsFirstPlayerToken.return_value = True
                with (
                    patch.object(
                        Engine,
                        "game",
                        game,
                        create=True,
                    ),
                    patch.object(
                        Engine,
                        "statistics",
                        statistics,
                        create=True,
                    ),
                ):
                    world.Initialize()

                self.assertFalse(world.is_game_over)
                self.assertEqual(world.phase.state, Phase.State.InitFinished)
                villain = world.GetScenario().GetVillain(None)
                self.assertIsNotNone(villain)
                self.assertEqual(villain.paper.card_id, "60077" if expert else "60076")
                charge = villain.GetInventoryDeck().FindCard(name="Electric Charge")
                self.assertIsNotNone(charge)
                self.assertEqual(charge.GetCounters("charge"), 2)

    def test_purple_man_reaches_first_player_turn_on_standard_and_expert(self):
        hero_json = (ROOT / "deck/starter/spider_man.json").read_text(
            encoding="utf-8"
        )

        for expert in (False, True):
            with self.subTest(expert=expert):
                suffix = "_expert" if expert else ""
                scenario = json.loads(
                    (ROOT / f"data/scenarios/the_getaway{suffix}.json").read_text(
                        encoding="utf-8"
                    )
                )
                underling = json.loads(
                    (ROOT / "data/encounter_sets/purple_man.json").read_text(
                        encoding="utf-8"
                    )
                )
                scenario["villain"] = underling[
                    "expert_villain" if expert else "villain"
                ]
                scenario["set_aside"] += underling["set_aside"]
                scenario["encounters"] += underling["encounters"]

                scene = SceneLoader.NewFromJson(
                    json.dumps(scenario),
                    scenario["encounter_sets"] + scenario["modular_sets"],
                    [hero_json],
                    60097,
                    [
                        "v18_all",
                        "disable_setup_draw_cards",
                        "disable_resolve_mulligans",
                    ],
                    {},
                )
                manager = Mock()
                manager.skip.is_skipping = True
                manager.undo.GetFastUndoHandle.return_value = None
                controller = Mock(manager=manager)
                world = World(scene, [controller])
                world.rule.SetRule(scene.rules, scene.is_puzzle, scene.seed)
                world.insert = CardFactory.GenerateCard(
                    "rule_a,rule_b",
                    world.area_insert,
                    world,
                    ui_render=False,
                ).face

                statistics = Mock()
                statistics.CanRegisterAbility.return_value = False
                game = Mock()
                game.controller_manager = manager
                game.state.is_running = True
                game.session.version.IsFirstPlayerToken.return_value = True
                with (
                    patch.object(
                        Engine,
                        "game",
                        game,
                        create=True,
                    ),
                    patch.object(
                        Engine,
                        "statistics",
                        statistics,
                        create=True,
                    ),
                ):
                    world.Initialize()

                self.assertFalse(world.is_game_over)
                self.assertEqual(world.phase.state, Phase.State.InitFinished)
                villain = world.GetScenario().GetVillain(None)
                self.assertIsNotNone(villain)
                self.assertEqual(
                    villain.paper.card_id,
                    "60098" if expert else "60097",
                )

    def test_remaining_underlings_reach_first_player_turn_on_both_difficulties(self):
        cases = (
            ("hammerhead", ("60086",), ("60087",), 60086),
            ("typhoid_mary", ("60110a", "60110b"), ("60111a", "60111b"), 60110),
        )
        for underling_id, standard_stage, expert_stage, seed in cases:
            underling = json.loads(
                (ROOT / f"data/encounter_sets/{underling_id}.json").read_text(
                    encoding="utf-8"
                )
            )
            for expert in (False, True):
                suffix = "_expert" if expert else ""
                scenario = json.loads(
                    (ROOT / f"data/scenarios/the_getaway{suffix}.json").read_text(
                        encoding="utf-8"
                    )
                )
                scenario["villain"] = underling[
                    "expert_villain" if expert else "villain"
                ]
                scenario["set_aside"] += underling.get("set_aside", [])
                scenario["encounters"] += underling["encounters"]

                with self.subTest(underling=underling_id, expert=expert):
                    world = self.initialize_world(scenario, seed + int(expert))
                    self.assertFalse(world.is_game_over)
                    self.assertEqual(world.phase.state, Phase.State.InitFinished)
                    villain = world.GetScenario().GetVillain(None)
                    self.assertIsNotNone(villain)
                    self.assertIn(
                        villain.paper.card_id,
                        expert_stage if expert else standard_stage,
                    )

    def test_kingpin_reaches_first_player_turn_on_standard_and_expert(self):
        for expert in (False, True):
            suffix = "_expert" if expert else ""
            scenario = json.loads(
                (ROOT / f"data/scenarios/kingpin{suffix}.json").read_text(
                    encoding="utf-8"
                )
            )
            with self.subTest(expert=expert):
                world = self.initialize_world(scenario, 60159 + int(expert))
                self.assertFalse(world.is_game_over)
                self.assertEqual(world.phase.state, Phase.State.InitFinished)
                villain = world.GetScenario().GetVillain(None)
                self.assertIsNotNone(villain)
                self.assertEqual(
                    villain.paper.card_id,
                    "60160a" if expert else "60159a",
                )
                public_support = world.area_environment.FindCard(
                    name="Public Support"
                )
                self.assertIsNotNone(public_support)

    def test_every_first_slice_card_has_metadata_and_creates_a_face(self):
        world = Mock()
        world.GetPlayerNumIcon.return_value = 1

        with patch.object(Build, "release", False):
            for card_id in CARD_IDS:
                with self.subTest(card_id=card_id):
                    paper = CardsDB.FindCardPaper(card_id)
                    face = CardFactory.CreateFace(paper, world)
                    self.assertEqual(face.paper.card_id, card_id)

    def test_every_first_slice_script_builds_abilities(self):
        for module_name in SCRIPT_MODULES:
            with self.subTest(module=module_name):
                abilities = importlib.import_module(module_name).GetAbilities()
                self.assertTrue(abilities)


class FearNoEvilCardBehaviorTests(unittest.TestCase):

    def test_replaced_boost_card_stays_available_and_is_not_attached(self):
        enemy = Mock()
        enemy.card.CastTo.return_value = Mock()
        enemy.components.boostable.GiveBoostCard.return_value = True
        boost_card = Mock()
        effect = Mock()
        would_message = Mock(is_be_instead=True)

        with patch.object(
            Message,
            "WhenEnemyWouldBeGivenBoostCard",
            return_value=would_message,
        ):
            given = CanBoost.GiveBoostCard(enemy, boost_card, effect)

        self.assertFalse(given)
        would_message.Send.assert_called_once_with()
        boost_card.card.visible.Update.assert_not_called()
        enemy.components.boostable.GiveBoostCard.assert_not_called()

    def test_public_support_replaces_boost_with_support_counter(self):
        module = importlib.import_module("cards.pack.fne.kingpin.60163b")
        ability = next(
            ability for ability in module.GetAbilities()
            if ability.when is Message.WhenEnemyWouldBeGivenBoostCard
        )
        support = Mock()
        support.GetCounters.return_value = 2
        effect = Mock()
        effect.this = support
        effect.this.CastTo.return_value = support
        message = Mock()

        with (
            patch.object(Worlds, "ConvertPerPlayerIconToInt", return_value=1),
            patch.object(Faces, "RemoveCountersOn") as remove,
        ):
            self.assertTrue(ability.conditions[-1](effect, message))
            ability.operation(effect, message)

        message.SetBeInstead.assert_called_once_with(effect)
        remove.assert_called_once_with([support], 1, "support", effect)

    def test_hammerhead_headbutt_stuns_then_damages_stunned_target(self):
        module = importlib.import_module("cards.pack.fne.hammerhead.60088")
        ability = module.GetAbilities()[0]
        hammerhead = Mock()
        effect = Mock()
        effect.this.CastTo.return_value = hammerhead
        fresh_target = Mock()
        fresh_target.IsStunned.return_value = False
        stunned_target = Mock()
        stunned_target.IsStunned.return_value = True
        message = Mock(attacked_targets=[fresh_target, stunned_target])

        with patch.object(Faces, "GiveStatus") as give_status:
            ability.operation(effect, message)

        give_status.assert_called_once_with([fresh_target], "Stunned", effect)
        hammerhead.DealDamage.assert_called_once_with(
            [stunned_target], 2, effect
        )

    def test_typhoid_mary_defeat_is_replaced_and_advances_psyche(self):
        module = importlib.import_module("cards.pack.fne.typhoid_mary")
        ability = module.MaryDefeatReplacement("13*")
        villain = Mock()
        psyche = Mock()
        psyche.GetCounters.return_value = 1
        effect = Mock()
        message = Mock()
        message.trigger.CastTo.return_value = villain

        with (
            patch.object(Worlds, "FindCardOnField", return_value=psyche),
            patch.object(Faces, "PlaceCountersOn") as place,
            patch.object(module, "CheckDisturbedPsycheVictory") as check_victory,
        ):
            ability.operation(effect, message)

        message.SetBeInstead.assert_called_once_with(effect)
        place.assert_called_once_with([psyche], 1, "damage", effect)
        villain.ResetHealth.assert_called_once_with(effect, "13*")
        check_victory.assert_called_once_with(effect)

    def test_spot_redirects_alternating_attack_damage_to_attacker(self):
        module = importlib.import_module("cards.pack.fne.kingpin.60171")
        ability = next(
            ability for ability in module.GetAbilities()
            if ability.when is Message.WhenUnitWouldTakeDamage
        )
        spot = Mock()
        spot.GetCounters.return_value = 1
        attacker = Mock()
        effect = Mock()
        effect.this.CastTo.return_value = spot
        message = Mock(attacker=attacker)

        with patch.object(Faces, "RemoveCountersOn") as remove:
            ability.operation(effect, message)

        remove.assert_called_once_with([spot], 1, "spot", effect)
        message.ChangeDealtToTarget.assert_called_once_with(attacker, effect)

    def test_bullseye_spine_caps_each_damage_instance_at_three(self):
        module = importlib.import_module("cards.pack.fne.bullseye.60068a")
        ability = next(
            ability for ability in module.GetAbilities()
            if ability.when is Message.WhenUnitWouldTakeDamage
        )
        attachment = Mock()
        attachment.GetCounters.return_value = 6
        attachment.card = Mock()
        effect = Mock()
        effect.this.CastTo.return_value = attachment
        message = Mock(will_take_damage=7)

        with patch.object(Faces, "PlaceCountersOn") as place:
            ability.operation(effect, message)

        message.PreventDamage.assert_called_once_with(4, effect)
        place.assert_called_once_with([attachment], 4, "damage", effect)
        attachment.card.Flip.assert_called_once_with(effect)

    def test_getaway_setup_uses_two_speed_on_expert(self):
        module = importlib.import_module("cards.pack.fne.the_getaway.60128a")
        ability = module.GetAbilities()[0]
        scheme = Mock()
        villain = Mock()
        effect = Mock()
        effect.this.CastTo.return_value = scheme

        with (
            patch.object(Worlds, "IsExpert", return_value=True),
            patch.object(Worlds, "FindVillain", return_value=villain),
            patch.object(Faces, "PlaceCountersOn") as place,
            patch("cards.pack.fne.the_getaway.60128a.SetupCards.AttachTo") as attach,
        ):
            ability.operation(effect, Mock())

        place.assert_called_once_with([scheme], 2, "speed", effect)
        attach.assert_called_once_with(
            effect,
            attach_to=villain,
            name="Out Front",
            card_type=importlib.import_module(
                "cards.pack.fne.the_getaway.60128a"
            ).Attachment,
        )

    def test_out_front_redirects_villain_damage_to_main_scheme_threat(self):
        module = importlib.import_module("cards.pack.fne.the_getaway.60129a")
        ability = next(
            ability for ability in module.GetAbilities()
            if ability.when is Message.WhenUnitWouldTakeDamage
        )
        attachment = Mock()
        scheme = Mock()
        effect = Mock()
        effect.this.CastTo.return_value = attachment
        message = Mock(will_take_damage=5)

        with patch.object(module, "GetGetaway", return_value=scheme):
            ability.operation(effect, message)

        message.PreventDamage.assert_called_once_with("All", effect)
        scheme.RemoveThreatFromSchemes.assert_called_once_with(
            [scheme],
            5,
            effect,
            ignore_crisis=True,
        )

    def test_vehicle_attachment_absorbs_damage_until_its_limit(self):
        module = importlib.import_module("cards.pack.fne.drive")
        ability = module.VehicleDamageAbility(4)
        attachment = Mock()
        attachment.GetCounters.return_value = 4
        effect = Mock()
        effect.this.CastTo.return_value = attachment
        message = Mock(will_take_damage=4)

        with (
            patch.object(Faces, "PlaceCountersOn") as place,
            patch.object(Faces, "DiscardAll") as discard,
        ):
            ability.operation(effect, message)

        message.PreventDamage.assert_called_once_with("All", effect)
        place.assert_called_once_with([attachment], 4, "damage", effect)
        discard.assert_called_once_with([attachment], effect)

    def test_traffic_jam_redirects_character_threat_to_itself(self):
        module = importlib.import_module("cards.pack.fne.drive.60189")
        ability = next(
            ability for ability in module.GetAbilities()
            if ability.when is Message.WhenCardWouldBePlacedToken
        )
        scheme = Mock()
        source = Mock()
        effect = Mock()
        effect.this.CastTo.return_value = scheme
        message = Mock(num=3, token_name="threat")
        message.by_effect.this = source

        # The destination is a scheme. Traffic Jam must inspect the character
        # that caused the threat change, carried by message.by_effect.this.
        with patch.object(
            module.CardFinder,
            "Check",
            autospec=True,
            return_value=True,
        ) as check:
            self.assertTrue(ability.conditions[-1](effect, message))

        check.assert_called_once_with(ANY, source, effect)

        ability.operation(effect, message)

        message.SetBeInstead.assert_called_once_with(effect)
        scheme.PlaceThreatOnSchemes.assert_called_once_with(
            [scheme], 3, effect
        )

    def test_carjacking_can_attach_discarded_vehicle_to_identity(self):
        module = importlib.import_module("cards.pack.fne.drive.60190")
        ability = module.GetAbilities()[0]
        attachment = Mock()
        attachment.traits = ["VEHICLE"]
        identity = Mock()
        identity.GetAttachedAttachments.return_value = []
        player = Mock()
        player.GetIdentity.return_value = identity
        player.AskSpendResources.return_value = True
        message = Mock()
        message.GetToPlayer.return_value = player
        effect = Mock()

        with patch.object(
            Worlds,
            "DiscardEncounterCardsUntil",
            return_value=attachment,
        ):
            ability.operation(effect, message)

        attachment.AttachTo2.assert_called_once_with(identity, effect)
        attachment.Reveal.assert_not_called()


if __name__ == "__main__":
    unittest.main()
