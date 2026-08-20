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
from game.card.face import Ally, Environment, Minion, Unit2, Upgrade
from game.card.factory import CardFactory
from game.message import Message
from game.operate.faces import Faces
from game.operate.worlds import Worlds
from game.scene.loader import SceneLoader
from game.world.phase import Phase
from game.world.world import World


ROOT = Path(__file__).resolve().parents[1]
PROTECTION_RACKET_IDS = [
    *[f"6013{value}{face}" for value in range(4, 9) for face in ("a", "b")],
    "60139", "60140", "60141",
]
DISASTER_IDS = [str(card_id) for card_id in range(60177, 60182)]
TRACKSUIT_IDS = [str(card_id) for card_id in range(60200, 60205)]


def load_card(package: str, card_id: str):
    return importlib.import_module(f"cards.pack.fne.{package}.{card_id}")


def setUpModule():
    Ver.Initialize()
    if not CardsDB.papers:
        CardsDB.Initialize()


class ProtectionRacketScenarioTests(unittest.TestCase):

    def load_scenario(self, expert: bool):
        suffix = "_expert" if expert else ""
        return json.loads(
            (ROOT / f"data/scenarios/protection_racket{suffix}.json").read_text(
                encoding="utf-8"
            )
        )

    def build_world(
        self,
        *,
        expert: bool,
        seed: int,
        selected_scheme: str | None = None,
    ):
        scenario = self.load_scenario(expert)
        underling = json.loads(
            (ROOT / "data/encounter_sets/bullseye.json").read_text(
                encoding="utf-8"
            )
        )
        scenario["villain"] = underling[
            "expert_villain" if expert else "villain"
        ]
        scenario["set_aside"] = scenario.get("set_aside", []) + underling[
            "set_aside"
        ]
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
        controller = Mock(manager=manager)

        def choose_one(effects, *args, **kwargs):
            if selected_scheme:
                for effect in effects:
                    if any(
                        target.paper.card_id == selected_scheme
                        for target in effect.targets
                    ):
                        return effect, False
            return effects[0], False

        controller.ChoiceOne.side_effect = choose_one
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
        Random.SetSeed(seed)

        def choose_scheme(faces, *args, **kwargs):
            if selected_scheme:
                for face in faces:
                    if face.paper.card_id == selected_scheme:
                        return face
            return faces[0] if faces else None

        with (
            patch.object(Engine, "game", game, create=True),
            patch.object(Engine, "statistics", statistics, create=True),
            patch.object(
                world.players[0],
                "AskChooseFace",
                side_effect=choose_scheme,
            ) if selected_scheme else patch.object(
                world.players[0],
                "AskChooseFace",
                wraps=world.players[0].AskChooseFace,
            ),
        ):
            world.Initialize()
        return world

    def test_scenario_contains_all_five_schemes_and_both_modular_sets(self):
        expected_schemes = [
            f"6013{value}a,6013{value}b" for value in range(4, 9)
        ]
        for expert in (False, True):
            scenario = self.load_scenario(expert)
            with self.subTest(expert=expert):
                self.assertEqual(scenario["schemes"], expected_schemes)
                self.assertEqual(
                    scenario["underling_sets"],
                    ["bullseye", "electro", "hammerhead", "purple_man", "typhoid_mary"],
                )
                self.assertEqual(
                    scenario["modular_sets"],
                    ["disasters", "tracksuit_mafia"],
                )
                self.assertEqual(
                    scenario["encounter_sets"],
                    ["standard", "expert"] if expert else ["standard"],
                )

    def test_modular_sets_have_the_printed_card_counts(self):
        disasters = json.loads(
            (ROOT / "data/encounter_sets/disasters.json").read_text(
                encoding="utf-8"
            )
        )
        tracksuits = json.loads(
            (ROOT / "data/encounter_sets/tracksuit_mafia.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(disasters["encounters"], DISASTER_IDS)
        self.assertEqual(len(tracksuits["encounters"]), 7)
        self.assertEqual(tracksuits["encounters"].count("60203"), 3)

    def test_standard_setup_uses_the_players_selected_scheme(self):
        world = self.build_world(
            expert=False,
            seed=55120,
            selected_scheme="60138a",
        )
        active = Worlds.GetMainSchemes(world.GetFirstGameArea())
        set_aside = world.aside_deck.FindCards(set_name="Protection Racket")

        self.assertFalse(world.is_game_over)
        self.assertEqual(world.phase.state, Phase.State.InitFinished)
        self.assertEqual([scheme.paper.card_id for scheme in active], ["60138b"])
        self.assertEqual(len(set_aside), 4)

    def test_expert_setup_is_deterministic_for_the_same_seed(self):
        selected = []
        for _ in range(2):
            world = self.build_world(expert=True, seed=55123)
            active = Worlds.GetMainSchemes(world.GetFirstGameArea())
            selected.append(active[0].paper.card_id)
            self.assertEqual(
                len(world.aside_deck.FindCards(set_name="Protection Racket")),
                4,
            )
        self.assertEqual(selected, ["60135b", "60135b"])

    def test_all_new_cards_have_metadata_and_build_a_face(self):
        world = Mock()
        world.GetPlayerNumIcon.return_value = 1
        for card_id in PROTECTION_RACKET_IDS + DISASTER_IDS + TRACKSUIT_IDS:
            with self.subTest(card_id=card_id):
                paper = CardsDB.FindCardPaper(card_id)
                face = CardFactory.CreateFace(paper, world)
                self.assertEqual(face.paper.card_id, card_id)


class ProtectionRacketSchemeTests(unittest.TestCase):

    def test_battle_in_bodega_damages_attacker_and_places_threat(self):
        module = load_card("protection_racket", "60134b")
        abilities = module.GetAbilities()
        attacker = Mock()
        effect = Mock()
        message = Mock(attacker=attacker)

        with patch.object(module, "PlaceThreatHere") as place:
            abilities[0].operation(effect, message)

        self.assertEqual(len(abilities), 2)
        attacker.TakeDamage.assert_called_once_with(effect.this, 1, effect)
        place.assert_called_once_with(effect)

    def test_bull_in_china_shop_counts_printed_excess_damage_targets(self):
        module = load_card("protection_racket", "60135b")
        ability = module.GetAbilities()[0]
        target = Mock()
        message = Mock(target=target, excess_damage=4)
        effect = Mock()

        with (
            patch.object(Ally, "IsType", return_value=False),
            patch.object(Minion, "IsType", return_value=True),
            patch.object(Worlds, "IsExpert", return_value=False),
        ):
            self.assertFalse(ability.conditions[-1](effect, message))
        with (
            patch.object(Ally, "IsType", return_value=False),
            patch.object(Minion, "IsType", return_value=True),
            patch.object(Worlds, "IsExpert", return_value=True),
            patch.object(module, "PlaceThreatHere") as place,
        ):
            self.assertTrue(ability.conditions[-1](effect, message))
            ability.operation(effect, message)
            place.assert_called_once_with(effect, 4)

    def test_hung_out_to_dry_damages_entering_character_and_places_threat(self):
        module = load_card("protection_racket", "60136b")
        ability = module.GetAbilities()[0]
        character = Mock()
        trigger = Mock()
        trigger.CastTo.return_value = character
        effect = Mock()

        with patch.object(module, "PlaceThreatHere") as place:
            ability.operation(effect, Mock(trigger=trigger))

        character.TakeDamage.assert_called_once_with(effect.this, 1, effect)
        place.assert_called_once_with(effect)

    def test_pawn_shop_discount_is_consumed_by_first_upgrade_each_round(self):
        module = load_card("protection_racket", "60137b")
        buff = module.PawnShopDiscount()
        upgrade = Mock()

        self.assertTrue(buff)
        with patch.object(Upgrade, "IsType", return_value=True):
            buff.OnRecordPlayedFace(upgrade)
        self.assertFalse(buff)
        buff.OnRoundEnd()
        self.assertTrue(buff)

        threat_response = module.GetAbilities()[1]
        with patch.object(module, "PlaceThreatHere") as place:
            threat_response.operation(Mock(), Mock())
        place.assert_called_once()

    def test_pizza_scheme_heals_defeating_character_and_places_threat(self):
        module = load_card("protection_racket", "60138b")
        ability = module.GetAbilities()[1]
        killer = Mock()
        killer.CastTo.return_value = killer
        effect = Mock()

        with (
            patch.object(Unit2, "IsType", return_value=True),
            patch.object(module, "PlaceThreatHere") as place,
        ):
            ability.operation(effect, Mock(killer=killer))

        killer.HealHealth.assert_called_once_with(1, effect)
        place.assert_called_once_with(effect)

    def test_each_scheme_has_the_printed_solo_loss_threshold(self):
        for value in range(4, 9):
            paper = CardsDB.FindCardPaper(f"6013{value}b")
            with self.subTest(card_id=paper.card_id):
                self.assertEqual(paper.desc["TargetThreat"], "10*")
                self.assertIn("players lose the game", paper.text)


class ProtectionRacketEncounterTests(unittest.TestCase):

    def test_change_of_venue_uses_same_swap_for_reveal_and_boost(self):
        module = load_card("protection_racket", "60141")
        abilities = module.GetAbilities()
        effect = Mock()
        with patch.object(module, "SwapProtectionRacketScheme") as swap:
            for ability in abilities:
                ability.operation(effect, Mock())
        self.assertEqual(swap.call_count, 2)
        self.assertTrue(any(
            ability.when is Message.WhenCardBecomeBoost for ability in abilities
        ))

    def test_shop_proprietor_places_four_threat_when_leaving_play(self):
        module = load_card("protection_racket", "60139")
        leave = next(
            ability for ability in module.GetAbilities()
            if ability.when is Message.AfterCardLeavePlay
        )
        scheme = Mock()
        effect = Mock()
        with patch.object(Worlds, "FindMainScheme", return_value=scheme):
            leave.operation(effect, Mock())
        effect.this.PlaceThreatOnSchemes.assert_called_once_with(
            [scheme], 4, effect
        )


class DisasterAndTracksuitTests(unittest.TestCase):

    def test_mystic_character_removes_two_civilians(self):
        module = load_card("disasters", "60177")
        action = module.GetAbilities()[1]
        character = Mock()
        character.HasTrait.return_value = True
        action.cost_funcs[0].return_exhausted_cards = [character]
        effect = Mock()

        with patch.object(Faces, "RemoveCountersOn") as remove:
            action.operation(effect, Mock())

        remove.assert_called_once_with(
            [effect.this], 2, "civilian", effect
        )

    def test_bystanders_searches_and_reveals_disaster_when_none_is_in_play(self):
        module = load_card("disasters", "60181")
        reveal = next(
            ability for ability in module.GetAbilities()
            if ability.when is Message.WhenCardRevealed
        )
        player = Mock()
        disaster = Mock()
        message = Mock()
        message.GetToPlayer.return_value = player
        effect = Mock()

        with (
            patch("cards.pack.fne.disasters.60181.ChooseDisaster", return_value=None),
            patch("cards.pack.fne.disasters.60181.Search.EncounterCard", return_value=disaster),
        ):
            reveal.operation(effect, message)

        disaster.Reveal.assert_called_once_with(player, effect)

    def test_tracksuit_defeat_tucks_minion_when_side_scheme_is_in_play(self):
        module = load_card("tracksuit_mafia", "60202")
        ability = module.GetAbilities()[0]
        minion = Mock()
        effect = Mock()
        effect.this.CastTo.return_value = minion

        with (
            patch.object(module, "TuckUnderTracksuitMafia", return_value=True) as tuck,
            patch.object(Faces, "GiveStatus") as status,
        ):
            ability.operation(effect, Mock(killer=Mock()))

        tuck.assert_called_once_with(effect, minion)
        status.assert_not_called()

    def test_tracksuit_mafia_reveals_tucked_minion_after_encounter_reveal(self):
        module = load_card("tracksuit_mafia", "60204")
        response = next(
            ability for ability in module.GetAbilities()
            if ability.when is Message.AfterCardRevealedEnd
        )
        tucked = Mock()
        scheme = Mock()
        scheme.GetPlacedCardArea.return_value.FindCards.return_value = [tucked]
        player = Mock()
        message = Mock()
        message.GetToPlayer.return_value = player
        effect = Mock()
        effect.this.CastTo.return_value = scheme

        response.operation(effect, message)

        tucked.Reveal.assert_called_once_with(player, effect)


if __name__ == "__main__":
    unittest.main()
