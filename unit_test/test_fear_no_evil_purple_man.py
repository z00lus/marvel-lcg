from __future__ import annotations

import importlib
import json
from pathlib import Path
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from engine import Engine  # noqa: F401
from cards.database import CardsDB
from engine.lib.version import Ver
from game.ability.ability_type import AbilityType
from game.card.face import (
    Ally,
    Attachment,
    Minion,
    Obligation,
    Support,
    Upgrade,
    Villain,
)
from game.card.factory import CardFactory
from game.effect.rule import GameRule
from game.message import Message
from game.scene.replay.campaign import CampaignDescriptor
from game.scene.replay.hero import HeroDescriptor
from game.scene.scene import Scene
from game.world.phase import Phase
from game.world.world import World


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = importlib.import_module("cards.pack.fne.purple_man")


def load_card(card_id: str):
    return importlib.import_module(f"cards.pack.fne.purple_man.{card_id}")


class PurpleManTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        Ver.Initialize()
        if not CardsDB.papers:
            CardsDB.Initialize()

    def make_world(self):
        manager = SimpleNamespace(skip=SimpleNamespace(is_skipping=True))
        scene = Scene(
            version=str(Ver.version),
            rules=["v18_all"],
            campaign=CampaignDescriptor(
                campaign_id="purple_man_test",
                name="Purple Man Test",
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
        identity = CardFactory.GenerateCard(
            "01001a,01001b",
            world.players[0].area_hero,
            world,
            ui_render=False,
        ).face
        identity.ResetHealth(GameRule(identity))
        world.phase.SetState(Phase.State.PlayerTurn)
        world.current_player = world.players[0]
        return world, world.players[0]

    def test_standard_and_expert_stage_pairs_are_registered(self):
        data = json.loads(
            (ROOT / "data/encounter_sets/purple_man.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(data["villain"], ["60097", "60098"])
        self.assertEqual(data["expert_villain"], ["60098", "60099"])

    def test_each_stage_grants_the_printed_influenced_keywords(self):
        expected = {
            "60097": {"guard": 1, "patrol": None, "villainous": None},
            "60098": {"guard": 1, "patrol": None, "villainous": 1},
            "60099": {"guard": 1, "patrol": 1, "villainous": 1},
        }
        for card_id, keywords in expected.items():
            with self.subTest(card_id=card_id):
                marker = Mock()
                with patch.object(
                    PACKAGE.AbilityFactory,
                    "GiveKeywordToInPlayWhenApplyThis",
                    return_value=[marker],
                ) as give:
                    abilities = load_card(card_id).GetAbilities()

                self.assertEqual(abilities, [marker])
                give.assert_called_once_with(
                    PACKAGE.INFLUENCED_MINION,
                    **keywords,
                )

    def test_converted_selects_highest_cost_ally_or_gains_surge(self):
        module = load_card("60100")
        reveal = next(
            ability for ability in module.GetAbilities()
            if ability.when is Message.WhenCardRevealed
        )
        attachment = Mock()
        low_cost = Mock()
        high_cost = Mock()
        player = Mock()
        player.GetControlAllies.return_value = [low_cost, high_cost]
        effect = Mock()
        effect.this.CastTo.return_value = attachment
        message = Mock()
        message.GetToPlayer.return_value = player

        with patch.object(PACKAGE.Filter, "One", return_value=high_cost):
            reveal.operation(effect, message)

        attachment.AttachTo2.assert_called_once_with(high_cost, effect)

        player.GetControlAllies.return_value = []
        with patch.object(module, "ThisCardGainSurge") as surge:
            reveal.operation(effect, message)
        surge.assert_called_once_with(effect)

    def test_converted_uses_shared_ally_to_influenced_minion_rule(self):
        abilities = load_card("60100").GetAbilities()
        treat = next(
            ability for ability in abilities
            if "TreatAttachedCardAsMinion" in ability.func_names
        )
        self.assertEqual(treat.type, AbilityType.NonKeyword)
        template = CardsDB.FindCardPaper("influenced_minion")
        self.assertEqual(template.name, "Influenced Minion")
        self.assertIn("INFLUENCED", template.traits)

    def test_converted_turns_ally_into_encounter_owned_influenced_minion(self):
        world, player = self.make_world()
        ally = CardFactory.GenerateCard(
            "01002",
            player.hand_cards,
            world,
            ui_render=False,
        ).face
        ally.PutIntoPlay(player, GameRule(ally))
        converted = CardFactory.GenerateCard(
            "60100",
            world.GetScenario().encounter_deck,
            world,
            ui_render=False,
        ).face
        game = Mock()
        game.controller_manager = Mock()
        game.controller_manager.skip.is_skipping = True
        statistics = Mock()
        statistics.CanRegisterAbility.return_value = False

        with (
            patch.object(Engine, "game", game, create=True),
            patch.object(Engine, "statistics", statistics, create=True),
        ):
            converted.Reveal(player, GameRule(converted))

        influenced = ally.card.face
        self.assertIsInstance(influenced, Minion)
        self.assertEqual(influenced.printed_name, "Black Cat")
        self.assertIn("INFLUENCED", influenced.traits)
        self.assertEqual(influenced.printed_scheme, ally.printed_thwart)
        self.assertEqual(influenced.printed_attack, ally.printed_attack)
        self.assertTrue(influenced.IsInPlay())
        self.assertIs(converted.GetOwner(), world.GetScenario())
        self.assertIs(converted.GetBindFace(), influenced)

    def test_command_obligation_stays_encounter_owned_in_player_area(self):
        world, player = self.make_world()
        obligation = CardFactory.GenerateCard(
            "60105",
            world.GetScenario().encounter_deck,
            world,
            ui_render=False,
        ).face
        game = Mock()
        game.controller_manager = Mock()
        game.controller_manager.skip.is_skipping = True
        statistics = Mock()
        statistics.CanRegisterAbility.return_value = False

        with (
            patch.object(Engine, "game", game, create=True),
            patch.object(Engine, "statistics", statistics, create=True),
        ):
            obligation.Reveal(player, GameRule(obligation))

        self.assertIs(obligation.card.area, player.obligations_area)
        self.assertIs(obligation.GetOwner(), world.GetScenario())
        self.assertIs(obligation.GetBindFace(), player.GetIdentity())
        self.assertEqual(obligation.GetCounters("command"), 3)

        obligation.RemoveCountersInternal(
            3,
            "command",
            GameRule(obligation),
        )
        self.assertEqual(obligation.GetCounters("command"), 0)
        self.assertFalse(obligation.IsInPlay())
        self.assertTrue(obligation.card.area.flags.is_encounter_discard_pile)

    def test_power_of_suggestion_grants_influenced_only_to_minions(self):
        marker = Mock()
        with patch.object(
            PACKAGE.AbilityFactory,
            "GiveKeywordToInPlayWhenApplyThis",
            return_value=[marker],
        ) as give:
            abilities = load_card("60108").GetAbilities()

        self.assertIs(abilities[0], marker)
        give.assert_called_once_with(Minion, trait="INFLUENCED")

    def test_command_obligations_use_three_counters_and_forced_actions(self):
        for card_id in ("60105", "60106", "60107"):
            with self.subTest(card_id=card_id):
                paper = CardsDB.FindCardPaper(card_id)
                self.assertEqual(paper.desc["Uses"], "3,command")
                action = next(
                    ability for ability in load_card(card_id).GetAbilities()
                    if ability.type is AbilityType.ForcedAction
                )
                self.assertEqual(
                    [type(cost).__name__ for cost in action.cost_funcs],
                    ["Exhaust", "Counter"],
                )
                self.assertEqual(action.cost_funcs[1].name, "command")

    def test_fight_targets_only_heroes_or_allies_and_deals_two_damage(self):
        action = next(
            ability for ability in load_card("60105").GetAbilities()
            if ability.type is AbilityType.ForcedAction
        )
        source = Mock()
        target = Mock()
        effect = Mock(targets=[target])
        effect.this = source

        action.operation(effect, Mock())

        source.DealDamage.assert_called_once_with([target], 2, effect)

    def test_protect_and_serve_resolve_against_villain_and_main_scheme(self):
        villain = Mock()
        main_scheme = Mock()
        effect = Mock()
        protect = next(
            ability for ability in load_card("60106").GetAbilities()
            if ability.type is AbilityType.ForcedAction
        )
        serve = next(
            ability for ability in load_card("60107").GetAbilities()
            if ability.type is AbilityType.ForcedAction
        )

        with (
            patch.object(PACKAGE.Worlds, "FindVillain", return_value=villain),
            patch.object(PACKAGE.Faces, "GiveStatus") as give_status,
        ):
            protect.operation(effect, Mock())
        give_status.assert_called_once_with([villain], "Tough", effect)

        with patch.object(
            PACKAGE.Worlds,
            "FindMainScheme",
            return_value=main_scheme,
        ):
            serve.operation(effect, Mock())
        effect.this.PlaceThreatOnSchemes.assert_called_once_with(
            [main_scheme], 2, effect
        )

    def test_purple_man_boost_is_dealt_after_the_activation(self):
        ability = PACKAGE.PurpleManBoostAbility()
        card = Mock()
        player = Mock()
        effect = Mock(this=card)
        message = Mock()
        message.GetToPlayer.return_value = player
        callback = None

        def remember_callback(_effect, operation):
            nonlocal callback
            callback = operation

        message.AfterThisActivation.side_effect = remember_callback
        ability.operation(effect, message)

        self.assertIsNotNone(callback)
        player.DealEncounterCard.assert_not_called()
        callback()
        player.DealEncounterCard.assert_called_once_with(card, effect)

    def test_influenced_minion_when_defeated_effects_use_printed_targets(self):
        main_scheme = Mock()
        judge_effect = Mock()
        judge = next(
            ability for ability in load_card("60102").GetAbilities()
            if ability.when is Message.WhenUnitBeDefeated
        )
        with patch.object(
            PACKAGE.Worlds,
            "FindMainScheme",
            return_value=main_scheme,
        ):
            judge.operation(judge_effect, Mock())
        judge_effect.this.PlaceThreatOnSchemes.assert_called_once_with(
            [main_scheme], 3, judge_effect
        )

        weak_ally = Mock(attack=1)
        strong_ally = Mock(attack=3)
        guard_effect = Mock()
        guard = next(
            ability for ability in load_card("60103").GetAbilities()
            if ability.when is Message.WhenUnitBeDefeated
        )
        with (
            patch.object(
                PACKAGE.Worlds,
                "GetOnFieldAllies",
                return_value=[weak_ally, strong_ally],
            ),
            patch.object(PACKAGE.Filter, "One", return_value=strong_ally) as choose,
            patch.object(PACKAGE.Faces, "DiscardAll") as discard,
        ):
            guard.operation(guard_effect, Mock())
        choose.assert_called_once_with(
            [weak_ally, strong_ally],
            guard_effect,
            highest_atk=True,
        )
        discard.assert_called_once_with([strong_ally], guard_effect)

        identity = Mock()
        player = Mock()
        player.GetIdentity.return_value = identity
        punk_effect = Mock()
        punk_message = Mock()
        punk_message.GetKillerPlayer.return_value = player
        punk = next(
            ability for ability in load_card("60104").GetAbilities()
            if ability.when is Message.WhenUnitBeDefeated
        )
        punk.operation(punk_effect, punk_message)
        identity.TakeDamage.assert_called_once_with(
            punk_effect.this, 3, punk_effect
        )

    def test_firefighter_attack_pierces_and_defeat_discards_highest_cost_asset(self):
        abilities = load_card("60101").GetAbilities()
        attack = next(
            ability for ability in abilities
            if ability.when is Message.WhenUnitWouldAttack
        )
        defeated = next(
            ability for ability in abilities
            if ability.when is Message.WhenUnitBeDefeated
        )
        effect = Mock()
        attack_message = Mock()
        attack.operation(effect, attack_message)
        attack_message.GainPiercing.assert_called_once_with(effect)

        low_cost = Mock(spec=Support)
        high_cost = Mock(spec=Upgrade)
        with (
            patch.object(
                PACKAGE.Worlds,
                "GetOnFieldCards",
                return_value=[low_cost, high_cost],
            ),
            patch.object(PACKAGE.Filter, "One", return_value=high_cost) as choose,
            patch.object(PACKAGE.Faces, "DiscardAll") as discard,
        ):
            defeated.operation(effect, Mock())
        choose.assert_called_once_with(
            [low_cost, high_cost],
            effect,
            highest_cost=True,
        )
        discard.assert_called_once_with([high_cost], effect)

    def test_sway_the_masses_only_reveals_influenced_discarded_minion(self):
        module = load_card("60109")
        reveal = next(
            ability for ability in module.GetAbilities()
            if ability.when is Message.WhenCardRevealed
        )
        player = Mock()
        minion = Mock()
        effect = Mock()
        message = Mock()
        message.GetToPlayer.return_value = player

        with patch.object(
            PACKAGE.Worlds,
            "GetEncounterDiscardPileCards",
            return_value=[minion],
        ) as find:
            reveal.operation(effect, message)

        find.assert_called_once_with(effect, PACKAGE.INFLUENCED_MINION)
        minion.Reveal.assert_called_once_with(player, effect)

        with (
            patch.object(
                PACKAGE.Worlds,
                "GetEncounterDiscardPileCards",
                return_value=[],
            ),
            patch.object(module, "ThisCardGainSurge") as surge,
        ):
            reveal.operation(effect, message)
        surge.assert_called_once_with(effect)


if __name__ == "__main__":
    unittest.main()
