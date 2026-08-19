from __future__ import annotations

import importlib
import json
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from engine import Engine  # noqa: F401
from cards.database import CardsDB
from engine.lib.random import Random
from engine.lib.version import Ver
from game.card.factory import CardFactory
from game.effect.rule import GameRule
from game.message import Message
from game.operate.faces import Faces
from game.operate.rand import Rand
from game.operate.worlds import Worlds
from game.scene.loader import SceneLoader
from game.statistics.game_history import GameHistory
from game.world.phase import Phase
from game.world.world import World


ROOT = Path(__file__).resolve().parents[1]
PERSONA_IDS = ("60153", "60154", "60155", "60156")


def load_card(card_id: str):
    return importlib.import_module(
        f"cards.pack.fne.stop_the_presses.{card_id}"
    )


def setUpModule():
    Ver.Initialize()
    if not CardsDB.papers:
        CardsDB.Initialize()


class StopThePressesScenarioTests(unittest.TestCase):

    def load_scenario(self, expert: bool):
        suffix = "_expert" if expert else ""
        return json.loads(
            (ROOT / f"data/scenarios/stop_the_presses{suffix}.json").read_text(
                encoding="utf-8"
            )
        )

    def build_world(
        self,
        *,
        underling_name: str="bullseye",
        expert: bool=False,
        seed: int=5600,
        selected_persona: str|None=None,
    ):
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

        original_random_choice = Rand.RandomChoice

        def choose_persona(candidates, effect):
            if selected_persona:
                for candidate in candidates:
                    if candidate.paper.card_id == selected_persona:
                        return candidate
            return original_random_choice(candidates, effect)

        with (
            patch.object(Engine, "game", game, create=True),
            patch.object(Engine, "statistics", statistics, create=True),
            patch.object(Rand, "RandomChoice", side_effect=choose_persona),
        ):
            world.Initialize()
        world._test_engine_game = game
        world._test_statistics = statistics
        return world

    def test_scenario_uses_required_sets_exactly_once(self):
        for expert in (False, True):
            scenario = self.load_scenario(expert)
            with self.subTest(expert=expert):
                self.assertEqual(
                    scenario["underling_sets"],
                    ["bullseye", "electro", "purple_man"],
                )
                self.assertEqual(
                    scenario["modular_sets"],
                    ["tombstone", "tracksuit_mafia"],
                )
                self.assertEqual(scenario["encounters"], ["60157", "60158", "60158"])
                self.assertEqual(
                    scenario["encounter_sets"],
                    ["standard", "expert"] if expert else ["standard"],
                )

    def test_setup_is_deterministic_for_the_same_seed(self):
        selected = []
        for _ in range(2):
            world = self.build_world(seed=56151)
            selected.append(
                world.players[0].supports.FindCard(trait="DAILY BUGLE").paper.card_id
            )
        self.assertEqual(selected[0], selected[1])

    def test_standard_and_expert_initialize_with_each_underling(self):
        for underling_name in ("bullseye", "electro"):
            for expert in (False, True):
                world = self.build_world(
                    underling_name=underling_name,
                    expert=expert,
                    seed=56100 + int(expert),
                )
                with self.subTest(underling=underling_name, expert=expert):
                    self.assertFalse(world.is_game_over)
                    self.assertEqual(world.phase.state, Phase.State.InitFinished)
                    self.assertEqual(
                        len(world.players[0].supports.FindCards(trait="DAILY BUGLE")),
                        1,
                    )

    def test_each_persona_can_be_selected_with_three_stamina(self):
        for persona_id in PERSONA_IDS:
            world = self.build_world(selected_persona=persona_id)
            player = world.players[0]
            persona = player.supports.FindCard(trait="DAILY BUGLE")
            removed_personas = world.area_removed.FindCards(trait="DAILY BUGLE")
            with self.subTest(persona_id=persona_id):
                self.assertFalse(world.is_game_over)
                self.assertEqual(world.phase.state, Phase.State.InitFinished)
                self.assertEqual(persona.paper.card_id, persona_id)
                self.assertEqual(persona.GetCounters("stamina"), 3)
                self.assertEqual(len(removed_personas), 3)
                self.assertEqual(
                    {face.paper.card_id for face in removed_personas},
                    set(PERSONA_IDS) - {persona_id},
                )
                self.assertIsNotNone(
                    world.area_environment.FindCard(card_ids=["60152"])
                )

    def test_personas_never_enter_normal_player_piles(self):
        world = self.build_world(selected_persona="60153")
        player = world.players[0]
        for area in (player.player_deck, player.hand_cards, player.discard_pile):
            with self.subTest(area=repr(area)):
                self.assertEqual(area.FindCards(trait="DAILY BUGLE"), [])

    def test_spending_final_stamina_ends_game_exactly_once(self):
        world = self.build_world(selected_persona="60153")
        persona = world.players[0].supports.FindCard(trait="DAILY BUGLE")
        with (
            patch.object(Engine, "game", world._test_engine_game, create=True),
            patch.object(
                Engine,
                "statistics",
                world._test_statistics,
                create=True,
            ),
            patch.object(
                world.game_over,
                "SetGameOver",
                wraps=world.game_over.SetGameOver,
            ) as set_game_over,
            patch.object(GameHistory, "CaptureOutcomeMetadata"),
        ):
            persona.RemoveCountersInternal(3, "stamina", GameRule(persona), forced=False)

        self.assertTrue(world.is_game_over)
        set_game_over.assert_called_once()
        self.assertEqual(world.players[0].discard_pile.FindCards(trait="DAILY BUGLE"), [])


class StopThePressesCardTests(unittest.TestCase):

    def test_all_scenario_scripts_load(self):
        expected_counts = {
            "60151a": 1,
            "60151b": 3,
            "60152": 1,
            "60153": 1,
            "60154": 1,
            "60155": 1,
            "60156": 1,
            "60157": 2,
            "60158": 2,
        }
        for card_id, expected_count in expected_counts.items():
            with self.subTest(card_id=card_id):
                self.assertEqual(len(load_card(card_id).GetAbilities()), expected_count)

    def test_ben_urich_looks_at_two_and_may_discard_one(self):
        ability = load_card("60153").GetAbilities()[0]
        player = Mock()
        cards = [Mock(), Mock()]
        player.LookAtDeck.return_value = cards
        effect = Mock()
        effect.GetInitiator.return_value = player

        ability.operation(effect, Mock())

        player.LookAtDeck.assert_called_once_with("EncounterDeck", 2, effect)
        player.AskDiscardFaces.assert_called_once_with(
            cards,
            (0, 1),
            effect,
            not_shuffle=True,
        )

    def test_betty_brant_cancels_boost_and_deals_replacement(self):
        ability = load_card("60154").GetAbilities()[0]
        effect = Mock()
        enemy = Mock()
        message = Mock()
        message.would_message.trigger.CastTo.return_value = enemy

        with patch.object(Faces, "GiveFacedownBoostCards") as give_boost:
            ability.operation(effect, message)

        message.CancelAllBoostIcons.assert_called_once_with(effect)
        message.CancelBoostAbility.assert_called_once_with(effect)
        give_boost.assert_called_once_with([enemy], 1, effect)

    def test_j_jonah_jameson_draws_two_after_costs(self):
        ability = load_card("60155").GetAbilities()[0]
        player = Mock()
        effect = Mock()
        effect.GetInitiator.return_value = player

        ability.operation(effect, Mock())

        player.DrawUp.assert_called_once_with(2, effect)

    def test_robbie_can_replace_the_dealt_encounter_card(self):
        ability = load_card("60156").GetAbilities()[0]
        player = Mock()
        initiator = Mock()
        card = Mock()
        initiator.MayChooseFace.return_value = card
        effect = Mock()
        effect.GetInitiator.return_value = initiator
        message = Mock()
        message.GetToPlayer.return_value = player
        message.would_message.face = card

        with (
            patch.object(Faces, "LookAt") as look_at,
            patch.object(Faces, "DiscardAll") as discard,
        ):
            ability.operation(effect, message)

        look_at.assert_called_once_with([card], initiator, effect)
        discard.assert_called_once_with([card], effect)
        player.DealEncounterCards.assert_called_once_with(1, effect)

    def test_exclusive_interview_exhausts_every_persona(self):
        module = load_card("60157")
        ability = next(
            ability for ability in module.GetAbilities()
            if ability.when is Message.WhenCardRevealed
        )
        supports = [Mock(), Mock()]
        effect = Mock()
        with (
            patch.object(
                module,
                "GetDailyBugleSupports",
                return_value=supports,
            ),
            patch.object(Faces, "ExhaustAll") as exhaust,
        ):
            ability.operation(effect, Mock())

        exhaust.assert_called_once_with(supports, effect)


if __name__ == "__main__":
    unittest.main()
