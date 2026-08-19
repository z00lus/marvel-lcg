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
from game.message import Message
from game.operate.faces import Faces
from game.operate.worlds import Worlds
from game.scene.loader import SceneLoader
from game.world.phase import Phase
from game.world.world import World


ROOT = Path(__file__).resolve().parents[1]
CARD_IDS = [
    "60065", "60066", "60067", "60068a", "60068b",
    *[str(card_id) for card_id in range(60069, 60076)],
    *[str(card_id) for card_id in range(60076, 60086)],
    *[str(card_id) for card_id in range(60097, 60110)],
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
]
SCRIPT_MODULES = [
    *(f"cards.pack.fne.bullseye.{card_id}" for card_id in (
        "60065", "60066", "60067", "60068a", "60068b",
        *[str(value) for value in range(60069, 60076)],
    )),
    *(f"cards.pack.fne.electro.{card_id}" for card_id in range(60076, 60086)),
    *(f"cards.pack.fne.purple_man.{card_id}" for card_id in range(60097, 60110)),
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
]


class FearNoEvilStructureTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        Ver.Initialize()
        if not CardsDB.papers:
            CardsDB.Initialize()

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
                    ["bullseye", "electro", "purple_man"],
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
            ["bullseye", "electro", "purple_man"],
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
