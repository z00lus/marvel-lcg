import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from engine import Engine  # noqa: F401 - establishes the project's import order
from cards.database import CardsDB
from cards.pack.mts.campaign import (
    AddRecordedCampaignCards,
    RevealCampaignSideScheme,
)
from engine.lib.version import Ver
from game.ability.factory.campaign import AbilityFactoryCampaign
from game.card.factory import CardFactory
from game.effect.rule import GameRule
from game.scene.replay.campaign import CampaignDescriptor
from game.scene.replay.hero import HeroDescriptor
from game.scene.scene import Scene
from game.world.world import World


ROOT = Path(__file__).resolve().parents[1]


class MadTitansShadowCampaignSetupTests(unittest.TestCase):

    def test_first_campaign_side_scheme_is_revealed_from_set_aside(self):
        world = Mock()
        effect = SimpleNamespace(world=world)
        aside = Mock(name="campaign set-aside")
        first_player = Mock(name="first player")
        face = Mock(name="Secure the Landing Pad")
        card = SimpleNamespace(face=face)

        with patch(
            "cards.pack.mts.campaign.Worlds.AsideDeck",
            return_value=aside,
        ), patch(
            "cards.pack.mts.campaign.Worlds.GetFirstPlayer",
            return_value=first_player,
        ), patch(
            "cards.pack.mts.campaign.CardFactory.GenerateCard",
            return_value=card,
        ) as generate:
            RevealCampaignSideScheme(1).operation(effect, Mock())

        generate.assert_called_once_with("21180a,21180b", aside, world)
        face.Reveal.assert_called_once_with(first_player, effect)

    def test_security_breach_is_shuffled_from_set_aside(self):
        world = Mock()
        effect = SimpleNamespace(world=world)
        aside = Mock(name="campaign set-aside")
        face = Mock(name="Security Breach")
        card = SimpleNamespace(face=face)

        with patch(
            "cards.pack.mts.campaign.Worlds.AsideDeck",
            return_value=aside,
        ), patch(
            "cards.pack.mts.campaign.Worlds.GetFirstPlayer",
        ), patch(
            "cards.pack.mts.campaign.CardFactory.GenerateCard",
            return_value=card,
        ) as generate, patch(
            "cards.pack.mts.campaign.Faces.ShuffleAllTo",
        ) as shuffle:
            AddRecordedCampaignCards(1).operation(effect, Mock())

        generate.assert_called_once_with("21181", aside, world)
        shuffle.assert_called_once_with([face], "EncounterDeck", effect)

    def test_ebony_maw_setup_moves_real_campaign_cards_to_their_destinations(self):
        Ver.Initialize()
        if not CardsDB.papers:
            CardsDB.Initialize()

        manager = SimpleNamespace(skip=SimpleNamespace(is_skipping=True))
        scene = Scene(
            version=str(Ver.version),
            rules=["mode_campaign", "v18_all"],
            campaign=CampaignDescriptor(
                campaign_id="mad_titans_shadow",
                name="Ebony Maw",
            ),
            players=[HeroDescriptor(
                version="",
                name="Spider-Man",
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
        CardFactory.GenerateCard(
            "01001a,01001b",
            world.players[0].area_hero,
            world,
            ui_render=False,
        )
        main_scheme = CardFactory.GenerateCard(
            "21074a,21074b",
            world.main_schemes_deck,
            world,
            ui_render=False,
        ).face

        # This focused test validates area transitions; unrelated trigger and
        # rendering behavior is covered by the event/reveal suites.
        world.event_manager.BroadcastMessage = lambda message: None
        effect = GameRule(main_scheme)
        RevealCampaignSideScheme(1).operation(effect, Mock())
        AddRecordedCampaignCards(1).operation(effect, Mock())

        self.assertEqual(
            [face.paper.card_id for face in world.area_schemes_side.GetAll()],
            ["21180a"],
        )
        self.assertEqual(
            [
                face.paper.card_id
                for face in world.GetScenario().encounter_deck.GetAll()
            ],
            ["21181"],
        )
        self.assertFalse(world.area_removed.GetAll())


class CampaignGeneratedCardAreaTests(unittest.TestCase):

    def test_shared_campaign_helper_puts_generated_card_in_set_aside(self):
        world = Mock()
        effect = SimpleNamespace(world=world)
        aside = Mock(name="campaign set-aside")
        face = Mock()
        card = SimpleNamespace(face=face)
        ability = AbilityFactoryCampaign.PutCardIntoPlay("campaign-card")

        with patch(
            "game.operate.worlds.Worlds.AsideDeck",
            return_value=aside,
        ), patch(
            "game.card.factory.CardFactory.GenerateCard",
            return_value=card,
        ) as generate:
            ability.operation(effect, Mock())

        generate.assert_called_once_with("campaign-card", aside, world)
        face.PutIntoPlay.assert_called_once_with(
            "FirstPlayer",
            effect,
            under_control=False,
        )

    def test_campaign_setup_never_uses_removed_area_as_staging(self):
        campaign_sources = [
            path
            for path in ROOT.glob("cards/pack/**/*.py")
            if "WhenCampaignSetup" in path.read_text(encoding="utf-8")
        ]
        campaign_sources.append(ROOT / "game/ability/factory/campaign.py")
        invalid_calls = []

        for path in campaign_sources:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                function = node.func
                if not isinstance(function, ast.Attribute):
                    continue
                if function.attr not in {"GenerateCard", "GenerateCards"}:
                    continue
                if len(node.args) < 2:
                    continue
                deck = node.args[1]
                if isinstance(deck, ast.Constant) and deck.value is None:
                    invalid_calls.append(f"{path.relative_to(ROOT)}:{node.lineno}")

        self.assertEqual(
            invalid_calls,
            [],
            "Campaign setup cards must be generated in set-aside, not removed",
        )


if __name__ == "__main__":
    unittest.main()
