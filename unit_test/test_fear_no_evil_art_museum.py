from __future__ import annotations

import importlib
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from engine import Engine  # noqa: F401
from cards.database import CardsDB
from engine.lib.random import Random
from engine.lib.version import Ver
from game.ability.ability_type import AbilityType
from game.card.face import Attachment, Enemy, Identity
from game.card.factory import CardFactory
from game.message import Message
from game.operate.faces import Faces
from game.operate.search import Search
from game.operate.worlds import Worlds
from game.scene.loader import SceneLoader
from game.world.phase import Phase
from game.world.world import World


ROOT = Path(__file__).resolve().parents[1]
ART_PACKAGE = importlib.import_module("cards.pack.fne.art_museum_heist")
OWL_PACKAGE = importlib.import_module("cards.pack.fne.the_owl")


def load_art_card(card_id: str):
    return importlib.import_module(f"cards.pack.fne.art_museum_heist.{card_id}")


def load_owl_card(card_id: str):
    return importlib.import_module(f"cards.pack.fne.the_owl.{card_id}")


def setUpModule():
    Ver.Initialize()
    if not CardsDB.papers:
        CardsDB.Initialize()


class ArtMuseumScenarioTests(unittest.TestCase):

    def load_scenario(self, expert: bool):
        suffix = "_expert" if expert else ""
        return json.loads(
            (ROOT / f"data/scenarios/art_museum_heist{suffix}.json").read_text(
                encoding="utf-8"
            )
        )

    def build_world(self, *, underling_name: str, expert: bool, seed: int):
        scenario = self.load_scenario(expert)
        underling = json.loads(
            (ROOT / f"data/encounter_sets/{underling_name}.json").read_text(
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
            [(ROOT / "deck/starter/spider_man.json").read_text(encoding="utf-8")],
            seed,
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

        statistics = Mock()
        statistics.CanRegisterAbility.return_value = False
        game = Mock()
        game.controller_manager = manager
        game.state.is_running = True
        game.session.version.IsFirstPlayerToken.return_value = True
        Random.SetSeed(seed)
        with (
            patch.object(Engine, "game", game, create=True),
            patch.object(Engine, "statistics", statistics, create=True),
        ):
            world.Initialize()
        return world

    def test_scenario_uses_exactly_one_underling_and_required_sets(self):
        for expert in (False, True):
            scenario = self.load_scenario(expert)
            with self.subTest(expert=expert):
                self.assertEqual(
                    scenario["underling_sets"],
                    ["bullseye", "electro", "purple_man"],
                )
                self.assertEqual(scenario["modular_sets"], ["cops", "the_owl"])
                self.assertEqual(scenario["encounters"].count("60127"), 2)
                self.assertEqual(len(scenario["encounters"]), 7)
                self.assertEqual(
                    scenario["encounter_sets"],
                    ["standard", "expert"] if expert else ["standard"],
                )

    def test_quick_game_payload_contains_one_underling_and_all_required_sets(self):
        for underling_name in ("bullseye", "electro"):
            scenario = self.load_scenario(False)
            underling = json.loads(
                (ROOT / f"data/encounter_sets/{underling_name}.json").read_text(
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
                53,
                ["v18_all"],
                {},
            )
            with self.subTest(underling=underling_name):
                self.assertEqual(scene.campaign.villain, underling["villain"])
                self.assertEqual(len(scene.campaign.encounters), 17)
                self.assertEqual(
                    scene.campaign.encounter_sets,
                    ["standard", "cops", "the_owl"],
                )

    def test_setup_attaches_one_random_art_and_leaves_three_in_encounter_deck(self):
        for underling_name in ("bullseye", "electro"):
            for expert in (False, True):
                world = self.build_world(
                    underling_name=underling_name,
                    expert=expert,
                    seed=5300 + int(expert),
                )
                villain = world.GetScenario().GetVillain(None)
                with self.subTest(underling=underling_name, expert=expert):
                    self.assertFalse(world.is_game_over)
                    self.assertEqual(world.phase.state, Phase.State.InitFinished)
                    self.assertEqual(
                        len(villain.GetInventoryDeck().FindCards(trait="ART")),
                        1,
                    )
                    self.assertEqual(
                        len(world.GetScenario().encounter_deck.FindCards(trait="ART")),
                        3,
                    )

    def test_setup_random_choice_is_deterministic_for_same_seed(self):
        selected = []
        for _ in range(2):
            world = self.build_world(
                underling_name="bullseye",
                expert=False,
                seed=53121,
            )
            villain = world.GetScenario().GetVillain(None)
            selected.append(
                villain.GetInventoryDeck().FindCard(trait="ART").paper.card_id
            )
        self.assertEqual(selected[0], selected[1])


class ArtMuseumCardTests(unittest.TestCase):

    def test_main_scheme_escalation_adds_one_for_each_art_on_villain(self):
        ability = next(
            ability for ability in load_art_card("60121b").GetAbilities()
            if ability.when is Message.CalcMainSchemeEscalation
        )
        villain = Mock()
        villain.GetInventoryDeck.return_value.FindCards.return_value = [Mock(), Mock()]
        effect = Mock()
        message = Mock(escalation_threat=1)

        with (
            patch.object(Worlds, "FindVillain", return_value=villain),
            patch.object(Worlds, "GetPlayerNumIcon", return_value=1),
        ):
            ability.operation(effect, message)

        self.assertEqual(message.escalation_threat, 3)

    def test_main_scheme_art_escalation_scales_per_player(self):
        ability = next(
            ability for ability in load_art_card("60121b").GetAbilities()
            if ability.when is Message.CalcMainSchemeEscalation
        )
        villain = Mock()
        villain.GetInventoryDeck.return_value.FindCards.return_value = [Mock(), Mock()]
        message = Mock(escalation_threat=2)

        with (
            patch.object(Worlds, "FindVillain", return_value=villain),
            patch.object(Worlds, "GetPlayerNumIcon", return_value=2),
        ):
            ability.operation(Mock(), message)

        self.assertEqual(message.escalation_threat, 6)

    def test_main_scheme_declares_the_printed_loss_condition(self):
        paper = CardsDB.FindCardPaper("60121b")
        self.assertIn(
            "<b>If this stage is completed, the players lose the game",
            paper.text,
        )

    def test_undefended_attack_returns_art_from_identity_to_villain(self):
        ability = next(
            ability for ability in load_art_card("60121b").GetAbilities()
            if ability.when is Message.AfterUnitAttackUnit
        )
        art = Mock()
        attacked = Mock()
        attacked.GetInventoryDeck.return_value.FindCards.return_value = [art]
        villain = Mock()
        player = Mock()
        effect = Mock()
        message = Mock(attacked=attacked)
        message.GetToPlayer.return_value = player

        with patch.object(Worlds, "FindVillain", return_value=villain):
            ability.operation(effect, message)

        art.AttachTo2.assert_called_once_with(villain, effect)

    def test_art_attachment_status_responses_use_new_host(self):
        expected = {
            "60122": "Confused",
            "60124": "Tough",
            "60125": "Stunned",
        }
        for card_id, status in expected.items():
            response = next(
                ability for ability in load_art_card(card_id).GetAbilities()
                if ability.when is Message.AfterCardAttachTo
            )
            host = Mock()
            effect = Mock()
            with self.subTest(card_id=card_id), patch.object(Faces, "GiveStatus") as give:
                response.operation(effect, Mock(to_face=host))
                give.assert_called_once_with([host], status, effect)

    def test_art_hero_action_offers_printed_resource_or_exhaust_cost(self):
        expected = {"60122": "B", "60123": "G", "60124": "R", "60125": "Y"}
        for card_id, resource in expected.items():
            action = next(
                ability for ability in load_art_card(card_id).GetAbilities()
                if ability.type is AbilityType.HeroAction
            )
            player = Mock()
            effect = Mock()
            message = Mock()
            message.GetToPlayer.return_value = player

            with self.subTest(card_id=card_id):
                action.operation(effect, message)
                choices = player.ChooseAbilities.call_args.args[1:]
                cost = choices[0].cost_fn(Mock(), [])
                self.assertEqual(getattr(cost, resource.lower()), 1)
                self.assertEqual(
                    choices[1].cost_funcs[0].__class__.__name__,
                    "Exhaust",
                )

    def test_art_thief_searches_deck_and_discard_before_identity_fallback(self):
        reveal = next(
            ability for ability in load_art_card("60126").GetAbilities()
            if ability.when is Message.WhenCardRevealed
        )
        player = Mock()
        villain = Mock()
        art = Mock()
        effect = Mock()
        message = Mock()
        message.GetToPlayer.return_value = player

        with (
            patch.object(Worlds, "FindVillain", return_value=villain),
            patch.object(Search, "EncounterCard", return_value=art) as search,
            patch.object(ART_PACKAGE, "MoveArtToVillain") as fallback,
        ):
            reveal.operation(effect, message)

        search.assert_called_once_with(
            effect,
            player,
            include_discard_pile=True,
            finder=ART_PACKAGE.ART,
        )
        art.AttachTo2.assert_called_once_with(villain, effect)
        fallback.assert_not_called()


class OwlCardTests(unittest.TestCase):

    def test_flight_serum_targets_only_non_aerial_enemies(self):
        self.assertIs(OWL_PACKAGE.NON_AERIAL_ENEMY.card_type, Enemy)
        self.assertEqual(OWL_PACKAGE.NON_AERIAL_ENEMY.non_trait, "AERIAL")
        action = next(
            ability for ability in load_owl_card("60191").GetAbilities()
            if ability.type is AbilityType.HeroAction
        )
        discard = action.cost_funcs[0]
        self.assertEqual(discard.__class__.__name__, "Discard")

    def test_mister_fish_engages_player_with_fewest_identity_hp(self):
        reveal = next(
            ability for ability in load_owl_card("60192").GetAbilities()
            if ability.when is Message.WhenCardRevealed
        )
        low_player = Mock()
        high_player = Mock()
        low_identity = Mock()
        high_identity = Mock()
        low_identity.GetControlByPlayer.return_value = low_player
        low_player.GetIdentity.return_value = low_identity
        high_player.GetIdentity.return_value = high_identity
        minion = Mock()
        effect = Mock()
        effect.this.CastTo.return_value = minion

        with (
            patch.object(Worlds, "GetPlayers", return_value=[high_player, low_player]),
            patch("cards.pack.fne.the_owl.60192.Filter.One", return_value=low_identity) as choose,
        ):
            reveal.operation(effect, Mock())

        choose.assert_called_once_with(
            [high_identity, low_identity],
            effect,
            fewest_remaining_hp=True,
        )
        minion.EngagePlayer.assert_called_once_with(low_player, effect)

    def test_owl_boost_grants_piercing_only_during_attack(self):
        boost = next(
            ability for ability in load_owl_card("60193").GetAbilities()
            if ability.when is Message.WhenCardBecomeBoost
        )
        effect = Mock()
        attack = Mock()
        boost.operation(effect, Mock(would_atk_message=attack))
        attack.GainPiercing.assert_called_once_with(effect)

    def test_swoop_down_activates_villain_then_each_engaged_minion(self):
        reveal = load_owl_card("60194").GetAbilities()[0]
        villain = Mock()
        villain.HasTrait.return_value = True
        minion = Mock()
        minion.HasTrait.return_value = False
        player = Mock()
        player.engaged_minions.GetAll.return_value = [minion]
        message = Mock()
        message.GetToPlayer.return_value = player
        effect = Mock()

        def activate(enemy):
            def run(player_arg, effect_arg, operation):
                operation(Mock(would_message=Mock()))
            enemy.DoActivate.side_effect = run

        activate(villain)
        activate(minion)
        with patch.object(Worlds, "FindVillain", return_value=villain):
            reveal.operation(effect, message)

        villain.DoActivate.assert_called_once()
        minion.DoActivate.assert_called_once()
        villain.GainForThisActive.assert_called_once()
        minion.GainForThisActive.assert_not_called()


if __name__ == "__main__":
    unittest.main()
