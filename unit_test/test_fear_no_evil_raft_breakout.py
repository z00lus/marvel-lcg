from __future__ import annotations

import importlib
import json
from pathlib import Path
import unittest
from unittest.mock import ANY, Mock, patch

from engine import Engine  # noqa: F401
from cards.database import CardsDB
from engine.lib.random import Random
from engine.lib.version import Ver
from game.ability.ability_type import AbilityType
from game.card.face import Ally, Attachment, Minion
from game.card.factory import CardFactory
from game.message import Message
from game.operate.faces import Faces
from game.operate.faces_counter import FacesCounter
from game.operate.worlds import Worlds
from game.scene.loader import SceneLoader
from game.world.phase import Phase
from game.world.world import World


ROOT = Path(__file__).resolve().parents[1]


def load_raft_card(card_id: str):
    return importlib.import_module(f"cards.pack.fne.the_raft_breakout.{card_id}")


def load_tombstone_card(card_id: str):
    return importlib.import_module(f"cards.pack.fne.tombstone.{card_id}")


def setUpModule():
    Ver.Initialize()
    if not CardsDB.papers:
        CardsDB.Initialize()


class RaftBreakoutScenarioTests(unittest.TestCase):

    def load_scenario(self, expert: bool):
        suffix = "_expert" if expert else ""
        return json.loads(
            (ROOT / f"data/scenarios/the_raft_breakout{suffix}.json").read_text(
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

    def test_scenario_uses_printed_sets_and_stages(self):
        expected_encounters = [str(card_id) for card_id in range(60144, 60151)]
        for expert in (False, True):
            scenario = self.load_scenario(expert)
            with self.subTest(expert=expert):
                self.assertEqual(
                    scenario["underling_sets"],
                    ["bullseye", "electro", "purple_man"],
                )
                self.assertEqual(scenario["modular_sets"], ["the_owl", "tombstone"])
                self.assertEqual(scenario["set_aside"], ["60143"])
                self.assertEqual(scenario["encounters"], expected_encounters)
                self.assertEqual(
                    scenario["encounter_sets"],
                    ["standard", "expert"] if expert else ["standard"],
                )

    def test_setup_attaches_master_key_and_reveals_one_prisoner(self):
        for underling_name in ("bullseye", "electro"):
            for expert in (False, True):
                world = self.build_world(
                    underling_name=underling_name,
                    expert=expert,
                    seed=54100 + int(expert),
                )
                villain = world.GetScenario().GetVillain(None)
                prisoners = [
                    minion for minion in world.players[0].GetEngagedMinions()
                    if minion.HasTrait("PRISONER")
                ]
                with self.subTest(underling=underling_name, expert=expert):
                    self.assertFalse(world.is_game_over)
                    self.assertEqual(world.phase.state, Phase.State.InitFinished)
                    self.assertEqual(
                        len(villain.GetInventoryDeck().FindCards(name="Master Key")),
                        1,
                    )
                    self.assertEqual(len(prisoners), 1)


class RaftBreakoutCardTests(unittest.TestCase):

    def test_prisoner_defeat_removes_two_for_elite_and_one_otherwise(self):
        delayed_ability = load_raft_card("60142b").GetAbilities()[0]
        scheme = Mock()
        effect = Mock()
        effect.this = scheme
        effect.ability = delayed_ability
        scheme.CastTo.return_value = scheme
        prisoner = Mock()
        would_message = Mock(trigger=prisoner)

        with patch(
            "game.ability.factory.defeated.Condition.CheckWhichCard",
            return_value=True,
        ):
            delayed_ability.operation(effect, would_message)

        registered_ability = scheme.effect.RegisterTemp.call_args.args[0]
        message = Mock(trigger=prisoner)
        prisoner.CastTo.return_value = prisoner

        for elite, expected in ((False, 1), (True, 2)):
            prisoner.HasTrait.return_value = elite
            registered_ability.operation(effect, message)
            with self.subTest(elite=elite):
                scheme.RemoveThreatFromSchemes.assert_called_with(
                    [scheme],
                    expected,
                    effect,
                    ignore_crisis=True,
                )
            scheme.RemoveThreatFromSchemes.reset_mock()

    def test_master_key_deals_only_minion_boost_cards(self):
        ability = next(
            ability for ability in load_raft_card("60143").GetAbilities()
            if ability.when is Message.AfterUnitSchemeEnd
        )
        player = Mock()
        minion = Mock()
        treachery = Mock()
        message = Mock(boost_cards=[minion, treachery])
        message.GetAgainstPlayer.return_value = player

        with patch.object(Minion, "IsType", side_effect=lambda face: face is minion):
            ability.operation(Mock(), message)

        player.DealEncounterCard.assert_called_once_with(minion, ANY)

    def test_absorbing_man_counts_resource_types_after_tucking_top_card(self):
        ability = load_raft_card("60144").GetAbilities()[0]
        this = Mock()
        top_card = Mock()
        player = Mock()
        player.player_deck.GetTop.return_value = top_card
        effect = Mock()
        effect.this.CastTo.return_value = this
        message = Mock()
        message.GetAgainstPlayer.return_value = player

        with patch.object(FacesCounter, "GetPrintedResourcesTypes", return_value=3):
            ability.operation(effect, message)

        this.TuckCardUnderHere.assert_called_once_with(top_card, effect)
        message.GainAttackForThisAttack.assert_called_once_with(3, effect)

    def test_baron_zemo_turns_the_chosen_ally_into_a_deceived_minion(self):
        module = load_raft_card("60145")
        ability = module.GetAbilities()[0]
        player = Mock()
        ally = Mock()
        ally.GetCounters.return_value = 0
        player.GetControlAllies.return_value = [ally]
        message = Mock()
        message.GetToPlayer.return_value = player
        effect = Mock()

        with (
            patch.object(Faces, "PlaceCountersOn") as place_counters,
            patch.object(module, "TreatAsMinion") as treat_as_minion,
        ):
            ability.operation(effect, message)

        place_counters.assert_called_once_with([ally], 1, "threat", effect)
        treat_as_minion.assert_called_once_with(
            ally,
            "Deceived Minion",
            player,
            effect,
        )

    def test_drang_adds_barrage_then_deals_that_much_indirect_damage(self):
        ability = load_raft_card("60146").GetAbilities()[0]
        drang = Mock()
        drang.CastTo.return_value = drang
        drang.GetCounters.return_value = 3
        player = Mock()
        message = Mock()
        message.GetAgainstPlayer.return_value = player
        effect = Mock(this=drang)

        with patch.object(Faces, "PlaceCountersOn") as place_counters:
            ability.operation(effect, message)

        place_counters.assert_called_once_with([drang], 1, "barrage", effect)
        player.GetIdentity().TakeIndirectDamage.assert_called_once_with(
            drang,
            3,
            effect,
        )

    def test_imprisoned_exposes_both_printed_discard_options(self):
        abilities = load_raft_card("60150").GetAbilities()
        names = {ability.name for ability in abilities}
        self.assertIn("Spend 3 resources to discard Imprisoned", names)
        self.assertIn(
            "Exhaust characters with at least 3 total THW to discard Imprisoned",
            names,
        )
        self.assertTrue(any(
            ability.when is Message.WhenCardBecomeBoost for ability in abilities
        ))


class TombstoneCardTests(unittest.TestCase):

    def test_condition_attachments_have_attach_and_forced_response_abilities(self):
        for card_id in ("60195", "60196"):
            abilities = load_tombstone_card(card_id).GetAbilities()
            with self.subTest(card_id=card_id):
                self.assertTrue(any(
                    ability.when is Message.WhenCardPutIntoPlay
                    for ability in abilities
                ))
                self.assertTrue(any(
                    ability.type is AbilityType.ForcedResponse
                    for ability in abilities
                ))

    def test_condition_responses_apply_the_printed_status_and_discard(self):
        first_player = Mock()
        attached_minion = Mock()
        cold_effect = Mock()
        hard_effect = Mock()
        hard_message = Mock(attacked_targets=[attached_minion])

        cold = next(
            ability for ability in load_tombstone_card("60195").GetAbilities()
            if ability.type is AbilityType.ForcedResponse
        )
        hard = next(
            ability for ability in load_tombstone_card("60196").GetAbilities()
            if ability.type is AbilityType.ForcedResponse
        )

        with (
            patch.object(Worlds, "GetFirstPlayer", return_value=first_player),
            patch.object(Faces, "GiveStatus") as give_status,
            patch.object(Faces, "DiscardAll") as discard_all,
        ):
            cold.operation(cold_effect, Mock())
            give_status.assert_called_once_with(
                [first_player.GetIdentity()],
                "Confused",
                cold_effect,
            )
            discard_all.assert_called_once_with([cold_effect.this], cold_effect)

            give_status.reset_mock()
            discard_all.reset_mock()
            hard.operation(hard_effect, hard_message)
            give_status.assert_called_once_with(
                [attached_minion],
                "Stunned",
                hard_effect,
            )
            discard_all.assert_called_once_with([hard_effect.this], hard_effect)

    def test_hit_list_removes_one_threat_for_each_defeated_ally(self):
        ability = load_tombstone_card("60199").GetAbilities()[0]
        scheme = Mock()
        scheme.CastTo.return_value = scheme
        first_player = Mock()
        defeated_ally = Mock(spec=Message.AfterUnitDefeatedUnit)
        defeated_ally.target = Mock()
        surviving_damage = Mock(spec=Message.AfterUnitTookDamage)
        first_player.GetIdentity().TakeIndirectDamage.return_value = [
            defeated_ally,
            surviving_damage,
        ]
        effect = Mock(this=scheme)

        with (
            patch.object(Worlds, "GetFirstPlayer", return_value=first_player),
            patch.object(Ally, "IsType", side_effect=lambda face: face is defeated_ally.target),
        ):
            ability.operation(effect, Mock())

        scheme.RemoveThreatFromSchemes.assert_called_once_with(
            [scheme],
            1,
            effect,
            ignore_crisis=True,
        )

    def test_rhino_and_tombstone_boosts_grant_tough(self):
        cases = (
            (load_raft_card("60149"), "activating"),
            (load_tombstone_card("60198"), "villain"),
        )
        for module, target_kind in cases:
            ability = next(
                ability for ability in module.GetAbilities()
                if ability.when is Message.WhenCardBecomeBoost
            )
            target = Mock()
            message = Mock(activating_enemy=target)
            effect = Mock()
            with (
                self.subTest(target=target_kind),
                patch.object(Worlds, "FindVillain", return_value=target),
                patch.object(Faces, "GiveStatus") as give,
            ):
                ability.operation(effect, message)
                give.assert_called_once_with([target], "Tough", effect)


if __name__ == "__main__":
    unittest.main()
