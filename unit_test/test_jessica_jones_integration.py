from __future__ import annotations

import importlib
import io
import json
from pathlib import Path
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from PIL import Image

# Preserve the application's normal import ordering.
from engine import Engine  # noqa: F401

from cards.database import CardsDB
from engine.lib.image_creator import ImageCreator
from engine.lib.random import Random
from engine.lib.version import Ver
from game.card.factory import CardFactory
from game.card.face.card_face import CardFace
from game.message import Message
from game.scene.loader import SceneLoader
from game.scene.replay.campaign import CampaignDescriptor
from game.scene.replay.hero import HeroDescriptor
from game.scene.scene import Scene
from game.world.limit_monitor.player_side_scheme_limit import PlayerSideSchemeLimit
from game.world.world import World


ROOT = Path(__file__).resolve().parents[1]

JESSICA_JONES_CARDS = [
    "61001a,61001b",
    *[f"610{number:02d}" for number in range(2, 15)],
    "61028",
    "61030",
    "61031",
    "61032",
    "61033a",
    "61033b",
    "61033c",
    "61039",
]


def load_card(module: str):
    return importlib.import_module(module)


class JessicaJonesIntegrationTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        Ver.Initialize()
        if not CardsDB.papers:
            CardsDB.Initialize()
        ImageCreator.Initialize()

    def make_world(self):
        manager = SimpleNamespace(skip=SimpleNamespace(is_skipping=True))
        scene = Scene(
            version=str(Ver.version),
            rules=["v18_all"],
            campaign=CampaignDescriptor(
                campaign_id="jessica_jones_test",
                name="Jessica Jones Test",
            ),
            players=[HeroDescriptor(
                version="",
                name="Jessica Jones",
                hero=[],
                hero_deck=[],
                obligations=[],
                nemesis_set=[],
                player_deck=[],
            )],
        )
        world = World(scene, [SimpleNamespace(manager=manager)])
        world.rule.SetRule(scene.rules, False, 1)
        world.insert = CardFactory.GenerateCard(
            "rule_a,rule_b",
            world.area_insert,
            world,
            ui_render=False,
        ).face
        return world

    def test_starter_deck_is_a_legal_forty_card_deck(self):
        starter = json.loads(
            (ROOT / "deck/starter/jessica_jones.json").read_text(
                encoding="utf-8",
            )
        )

        self.assertEqual(len(starter["hero_deck"]), 15)
        self.assertEqual(len(starter["player_deck"]), 25)
        self.assertEqual(
            len(starter["hero_deck"]) + len(starter["player_deck"]),
            40,
        )
        self.assertEqual(starter["hero"], ["61001a,61001b"])
        self.assertEqual(starter["set_aside"], ["61002"])
        self.assertEqual(starter["obligations"], ["61030"])
        self.assertEqual(
            starter["nemesis_set"],
            ["61031", "61032", "61033a", "61033b", "61033c"],
        )

    def test_every_integrated_card_can_create_a_real_card_face(self):
        world = self.make_world()
        player = world.players[0]
        encounter_cards = {
            "61030", "61031", "61032", "61033a", "61033b", "61033c",
        }

        for card_id in JESSICA_JONES_CARDS:
            with self.subTest(card_id=card_id):
                if card_id == "61001a,61001b":
                    area = player.area_hero
                elif card_id in encounter_cards:
                    area = world.GetScenario().encounter_deck
                else:
                    area = player.set_aside_deck

                card = CardFactory.GenerateCard(
                    card_id,
                    area,
                    world,
                    ui_render=False,
                )
                self.assertIsInstance(card.face, CardFace)

    def test_rhino_setup_puts_alias_investigations_into_play(self):
        scenario = json.loads(
            (ROOT / "data/scenarios/rhino.json").read_text(encoding="utf-8")
        )
        hero_json = (ROOT / "deck/starter/jessica_jones.json").read_text(
            encoding="utf-8",
        )
        scene = SceneLoader.NewFromJson(
            json.dumps(scenario),
            scenario["encounter_sets"] + scenario["modular_sets"],
            [hero_json],
            61001,
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
        world = World(scene, [Mock(manager=manager)])
        world.rule.SetRule(scene.rules, scene.is_puzzle, scene.seed)
        world.insert = CardFactory.GenerateCard(
            "rule_a,rule_b",
            world.area_insert,
            world,
            ui_render=False,
        ).face
        game = Mock()
        game.controller_manager = manager
        game.state.is_running = True
        game.session.version.IsFirstPlayerToken.return_value = True
        statistics = Mock()
        statistics.CanRegisterAbility.return_value = False
        Random.SetSeed(scene.seed)

        with (
            patch.object(Engine, "game", game, create=True),
            patch.object(Engine, "statistics", statistics, create=True),
        ):
            world.Initialize()

        player = world.players[0]
        alias = player.supports.FindCard(card_ids=["61002"])
        self.assertIsNotNone(alias)
        self.assertTrue(alias.IsInPlay())
        self.assertEqual(player.player_deck.GetSize(), 40)

    def test_jessica_specific_counter_names_are_registered(self):
        self.assertIn("evidence", CardFace.COUNTER_LIST)
        self.assertIn("pheromone", CardFace.COUNTER_LIST)

    def test_piecing_it_all_together_does_not_count_toward_limit(self):
        paper = Mock(card_id="61007")
        paper.IsFromSet.return_value = False
        self.assertFalse(
            PlayerSideSchemeLimit.CountsTowardLimit(
                SimpleNamespace(paper=paper),
            )
        )

        paper.card_id = "61028"
        self.assertTrue(
            PlayerSideSchemeLimit.CountsTowardLimit(
                SimpleNamespace(paper=paper),
            )
        )

    def test_circumstantial_evidence_observes_any_enemy_defeat(self):
        abilities = load_card(
            "cards.pack.jj.jessica_jones.61010",
        ).GetAbilities()

        self.assertEqual(len(abilities), 1)
        self.assertIs(abilities[0].when, Message.AfterUnitBeDefeated)

    def test_now_im_ticked_off_is_an_attack(self):
        abilities = load_card(
            "cards.pack.jj.jessica_jones.61012",
        ).GetAbilities()

        self.assertEqual(len(abilities), 1)
        self.assertTrue(abilities[0].is_like_attack)

    def test_purple_man_uses_the_highest_printed_character_powers(self):
        module = load_card(
            "cards.pack.jj.jessica_jones_nemesis.61031",
        )
        markers = [Mock(), Mock()]
        with patch.object(
            module.AbilityFactory,
            "GiveKeywordToInPlayWhenApplyThis",
            side_effect=[[markers[0]], [markers[1]]],
        ) as give_keyword:
            self.assertEqual(module.GetAbilities(), markers)

        attack_call, scheme_call = give_keyword.call_args_list
        highest_attack = attack_call.kwargs["get_new_value"]
        highest_scheme_or_thwart = scheme_call.kwargs["get_new_value"]
        purple_man = Mock()
        hero = SimpleNamespace(attack=2, thwart=3)
        minion = SimpleNamespace(attack=4, scheme=1)
        effect = Mock()

        with (
            patch.object(
                module.Worlds,
                "GetOnFieldCharacters",
                return_value=[purple_man, hero, minion],
            ),
            patch.object(
                module.HasAttack,
                "IsType",
                side_effect=lambda face: hasattr(face, "attack"),
            ),
            patch.object(
                module.HasScheme,
                "IsType",
                side_effect=lambda face: hasattr(face, "scheme"),
            ),
            patch.object(
                module.HasThwart,
                "IsType",
                side_effect=lambda face: hasattr(face, "thwart"),
            ),
        ):
            self.assertEqual(highest_attack(effect, purple_man), 4)
            self.assertEqual(highest_scheme_or_thwart(effect, purple_man), 3)

        self.assertEqual(attack_call.kwargs["base_atk"], 1)
        self.assertEqual(scheme_call.kwargs["base_sch"], 1)

    def test_suggestion_cancellation_falls_back_to_main_scheme_threat(self):
        module = load_card(
            "cards.pack.jj.jessica_jones_nemesis.suggestion",
        )
        action = module.SuggestionAbilities("R")[0]
        player = Mock()
        card = Mock()
        player.hand_cards.Get.return_value = [card]
        choices = []
        player.ChooseAbilities.side_effect = (
            lambda effect, *abilities: choices.extend(abilities)
        )
        effect = Mock()
        effect.GetInitiator.return_value = player

        with patch.object(module, "CardFinder") as card_finder:
            card_finder.return_value.Checks.return_value = [card]
            action.operation(effect, Mock())

        play_card = next(choice for choice in choices if choice.name.startswith("Play a card"))
        choice_effect = SimpleNamespace(
            targets=[card],
            GetPaidResources=Mock(return_value=Mock()),
        )
        player.PlayCardsLikeInTurn.return_value = []
        play_card.operation(choice_effect, Mock())

        player.PlayCardsLikeInTurn.assert_called_once_with(
            [card],
            effect,
            if_not_play_discard_it=False,
        )
        effect.this.PlaceThreatOnSchemes.assert_called_once_with(
            "MainScheme",
            2,
            effect,
        )

    def test_missing_art_is_rendered_as_a_readable_text_card(self):
        image_data = ImageCreator.CreateNoImage("61004")
        image = Image.open(io.BytesIO(image_data))

        self.assertEqual(image.size, (596, 834))
        self.assertGreater(len(image.getcolors(maxcolors=1_000_000) or []), 50)
        self.assertGreater(len(image_data), 20_000)

        side_scheme = Image.open(
            io.BytesIO(ImageCreator.CreateNoImage("61028"))
        )
        self.assertEqual(side_scheme.size, (596, 834))


if __name__ == "__main__":
    unittest.main()
