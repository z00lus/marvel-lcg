from __future__ import annotations

import importlib
import inspect
import json
import os
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

# Importing Engine first follows the application's normal import order and
# avoids the circular imports exposed by importing a numeric card module in
# isolation.  It does not initialize the engine or start a server.
from engine import Engine

from game.ability import AbilityType, CostFunc
from game.element.resources import Resources
from game.player.action.player_action import PlayerAction
from game.scene.loader import LoaderHelper, UnsupportedReplayRulesError
from game.scene.scene import Scene


ROOT = Path(__file__).resolve().parents[1]


def load_card(card_id: str):
    return importlib.import_module(f"cards.pack.wonder_man.{card_id}")


def closure_values(function):
    return inspect.getclosurevars(function).nonlocals


class PacifismTests(unittest.TestCase):

    def setUp(self):
        self.module = load_card("58025")
        self.abilities = self.module.GetAbilities()

    def test_prevents_wonder_man_from_attacking(self):
        cannot_attack = self.abilities[0]
        effect = Mock()
        message = Mock()

        cannot_attack.operation(effect, message)

        message.SetCannotAttack.assert_called_once_with(effect)

    def test_can_be_discarded_by_exhausting_simon_williams(self):
        action = self.abilities[1]
        obligation = Mock()
        effect = Mock(this=obligation)

        self.assertEqual(action.type, AbilityType.AlterEgoAction)
        self.assertEqual(action.name, "Exhaust Simon Williams")
        self.assertEqual(len(action.cost_funcs), 1)
        self.assertIsInstance(action.cost_funcs[0], CostFunc.Exhaust)
        self.assertEqual(
            action.cost_funcs[0].selector.selector_target.raw_target,
            "YourIdentity",
        )

        with patch.object(self.module.Faces, "DiscardAll", return_value=[obligation]) as discard:
            action.operation(effect, Mock())

        discard.assert_called_once_with([obligation], effect)

    def test_can_be_discarded_by_spending_exactly_three_tucked_cards(self):
        action = self.abilities[2]
        cost = action.cost_funcs[0]
        effect = Mock()
        cards = [MagicMock(), MagicMock(), MagicMock()]
        for card in cards:
            card.card.area = Mock()

        self.assertEqual(action.type, AbilityType.AlterEgoAction)
        self.assertEqual(
            action.name,
            "Discard 3 cards tucked under Ionic Physiology",
        )
        self.assertIsInstance(cost, CostFunc.Discard)
        self.assertEqual(cost.selector.selector_range.raw_range, (3, 3))

        with patch.object(self.module, "GetIonicCards", return_value=cards):
            self.assertEqual(
                cost.selector.selector_target.get_targets_fn(effect),
                cards,
            )

        with patch.object(self.module.Faces, "DiscardAll", return_value=cards) as discard:
            self.assertTrue(cost.call_fn(cards, effect, None))

        discard.assert_called_once_with(cards, effect)


class JetBeltCostTests(unittest.TestCase):

    def setUp(self):
        self.module = load_card("58008")
        self.cost = self.module.GetAbilities()[0].cost_funcs[0]

    def test_non_event_payment_requires_an_ionic_card(self):
        effect = Mock()
        effect.GetBindMessage.return_value = SimpleNamespace(
            for_effect=SimpleNamespace(this=Mock()),
        )
        self.cost.cost_legal_targets = []

        with (
            patch.object(self.cost.selector, "GetAllLegalTargets", return_value=[]),
            patch.object(self.module.Event, "IsType", return_value=False),
        ):
            self.assertFalse(self.cost.ValidatePreparedCost(effect))

    def test_event_payment_may_use_jet_belt_without_an_ionic_card(self):
        effect = Mock()
        effect.GetBindMessage.return_value = SimpleNamespace(
            for_effect=SimpleNamespace(this=Mock()),
        )
        self.cost.cost_legal_targets = []

        with (
            patch.object(self.cost.selector, "GetAllLegalTargets", return_value=[]),
            patch.object(self.module.Event, "IsType", return_value=True),
        ):
            self.assertTrue(self.cost.ValidatePreparedCost(effect))


class ScarletWitchTests(unittest.TestCase):

    @staticmethod
    def get_operation(module):
        sentinel = object()
        with patch.object(
            module.AbilityFactory,
            "AfterPlayerPlayedCard",
            return_value=sentinel,
        ) as factory:
            abilities = module.GetAbilities()

        assert abilities == [sentinel]
        args = factory.call_args.args
        assert args[:3] == (AbilityType.ForcedResponse, "You", "This")
        return args[3]

    def test_resolves_when_revealed_ability_of_discarded_treachery(self):
        module = load_card("58014")
        operation = self.get_operation(module)
        effect = Mock()
        initiator = Mock()
        ally = Mock()
        discarded = Mock()
        effect.GetInitiator.return_value = initiator
        effect.this.CastTo.return_value = ally

        with patch.object(module.Worlds, "DiscardEncounterTopCard", return_value=discarded), \
             patch.object(module.Treachery, "IsType", return_value=True):
            operation(effect, Mock())

        discarded.ResolveAbility.assert_called_once_with(
            initiator,
            AbilityType.WhenRevealed,
            effect,
        )

    def test_does_not_resolve_non_treachery_card(self):
        module = load_card("58014")
        operation = self.get_operation(module)
        effect = Mock()
        discarded = Mock()

        with patch.object(module.Worlds, "DiscardEncounterTopCard", return_value=discarded), \
             patch.object(module.Treachery, "IsType", return_value=False):
            operation(effect, Mock())

        discarded.ResolveAbility.assert_not_called()


class SwordsmanTests(unittest.TestCase):

    def setUp(self):
        self.abilities = load_card("58022").GetAbilities()

    def test_basic_attack_gains_piercing(self):
        effect = Mock()
        message = Mock()

        self.abilities[0].operation(effect, message)

        message.GainPiercing.assert_called_once_with(effect)

    def test_declares_swordsman_without_exhausting_him(self):
        response = self.abilities[1]
        effect = Mock()
        swordsman = Mock()
        message = Mock()
        effect.this.CastTo.return_value = swordsman

        response.operation(effect, message)

        message.would_atk_message.DeclareDefender.assert_called_once_with(
            swordsman,
            effect,
        )
        swordsman.Exhaust.assert_not_called()

    def test_defense_response_requires_an_undefended_attack(self):
        condition = self.abilities[1].const_condition[-1]
        effect = Mock()
        message = Mock()

        message.would_atk_message.defender = None
        self.assertTrue(condition(effect, message))

        message.would_atk_message.defender = Mock()
        self.assertFalse(condition(effect, message))


class StrongerTogetherTests(unittest.TestCase):

    def setUp(self):
        self.ability = load_card("58019").GetAbilities()[0]

    def test_reduces_damage_by_hero_defense(self):
        effect = Mock()
        hero = Mock(defense=3)
        message = Mock()
        effect.GetInitiator.return_value.GetHero.return_value = hero

        self.ability.operation(effect, message)

        message.ReduceDamage.assert_called_once_with(3, effect)

    def test_cannot_protect_the_hero_itself(self):
        condition = self.ability.const_condition[-1]
        effect = Mock()
        hero = Mock()
        effect.GetInitiator.return_value.GetHero.return_value = hero

        self.assertFalse(condition(effect, SimpleNamespace(trigger=hero)))
        self.assertTrue(condition(effect, SimpleNamespace(trigger=Mock())))

    def test_target_must_share_a_trait_with_the_hero(self):
        selector_filter = self.ability.selectors[0].selector_filter
        values = closure_values(selector_filter.FilterLegalTargets)

        self.assertTrue(values["share_trait_with_your_hero"])


class FirebirdTests(unittest.TestCase):

    def setUp(self):
        self.module = load_card("58012")
        self.enter_play, self.rebirth = self.module.GetAbilities()

    def test_overpay_places_one_rebirth_counter(self):
        effect = Mock()
        firebird = Mock()
        effect.this.CastTo.return_value = firebird

        with patch.object(self.module.Faces, "PlaceCountersOn") as place:
            self.enter_play.operation(effect, SimpleNamespace(overpaid=1))

        place.assert_called_once_with([firebird], 1, "rebirth", effect)

    def test_no_counter_without_overpay(self):
        effect = Mock()
        effect.this.CastTo.return_value = Mock()

        with patch.object(self.module.Faces, "PlaceCountersOn") as place:
            self.enter_play.operation(effect, SimpleNamespace(overpaid=0))

        place.assert_not_called()

    def test_consequential_defeat_is_replaced_and_all_damage_is_healed(self):
        effect = Mock()
        firebird = Mock()
        message = Mock()
        effect.this.CastTo.return_value = firebird

        self.rebirth.operation(effect, message)

        message.SetBeInstead.assert_called_once_with(effect)
        firebird.HealHealth.assert_called_once_with("All", effect)

    def test_rebirth_requires_one_counter_and_consequential_damage(self):
        self.assertEqual(len(self.rebirth.cost_funcs), 1)
        counter_cost = self.rebirth.cost_funcs[0]
        values = closure_values(counter_cost.call_fn)
        condition = self.rebirth.const_condition[-1]
        message = Mock()

        self.assertIsInstance(counter_cost, CostFunc.Counter)
        self.assertEqual(values["size"], 1)
        self.assertEqual(values["name"], "rebirth")

        message.IsByConsequentialDamage.return_value = True
        self.assertTrue(condition(Mock(), message))
        message.IsByConsequentialDamage.return_value = False
        self.assertFalse(condition(Mock(), message))


class GrimReaperTests(unittest.TestCase):

    def test_ally_controller_receives_a_facedown_encounter_card(self):
        module = load_card("58026")
        sentinel = object()
        with patch.object(
            module.AbilityFactory,
            "AfterUnitAttackAndDefeatUnit",
            return_value=sentinel,
        ) as factory:
            abilities = module.GetAbilities()

        self.assertEqual(abilities, [sentinel])
        args = factory.call_args.args
        self.assertEqual(args[:3], (AbilityType.ForcedResponse, "This", module.Ally))

        operation = args[3]
        effect = Mock()
        defeated_ally = Mock()
        controller = Mock()
        defeated_ally.GetControlByPlayer.return_value = controller

        operation(effect, SimpleNamespace(target=defeated_ally))

        controller.DealEncounterCards.assert_called_once_with(1, effect)


class EnergySiphonTests(unittest.TestCase):

    def setUp(self):
        self.module = load_card("58006")
        generated_ability = Mock()
        generated_ability.SetCostFunc.return_value = generated_ability
        check_ability = Mock()

        with patch.object(
            self.module.AbilityFactory,
            "DoDiscardThisToGenerateResources",
            return_value=generated_ability,
        ) as generate, patch.object(
            self.module.AbilityFactory,
            "CheckThisCanDropPay",
            return_value=check_ability,
        ) as check:
            abilities = self.module.GetAbilities()

        self.assertEqual(abilities, [generated_ability, check_ability])
        self.resource_function = generate.call_args.kwargs["res_fn"]
        self.damage_cost = generated_ability.SetCostFunc.call_args.args[0]
        check.assert_called_once()
        self.assertEqual(check.call_args.args[0].text, "YYYY")
        self.assertTrue(check.call_args.kwargs["spend_this_only_in_hero_form"])

    def test_generates_one_to_four_energy_for_zero_to_three_damage(self):
        effect = Mock()
        effect.cost_func.Get.return_value = self.damage_cost

        for damage in range(4):
            with self.subTest(damage=damage):
                self.damage_cost.return_damage = damage
                resources = self.resource_function(effect, Mock())
                self.assertEqual(resources.text, "Y" * (damage + 1))

    def test_damage_choice_cannot_defeat_the_identity(self):
        effect = Mock()
        player = Mock()
        identity = Mock()
        identity.CastTo.return_value = identity

        for health, selected_damage in ((1, 0), (2, 1), (3, 2), (4, 3)):
            with self.subTest(health=health):
                identity.health = health
                player.DeclareNumber.reset_mock()
                player.DeclareNumber.return_value = selected_damage
                with patch(
                    "game.ability.cost_func.TakeDamageOnCall",
                    return_value=True,
                ) as take_damage:
                    self.assertTrue(
                        self.damage_cost.call_fn([identity], effect, player)
                    )

                player.DeclareNumber.assert_called_once_with(
                    0,
                    min(3, health - 1),
                )
                if selected_damage:
                    take_damage.assert_called_once_with(
                        [identity],
                        selected_damage,
                        effect,
                    )
                else:
                    take_damage.assert_not_called()
                self.assertEqual(
                    self.damage_cost.return_damage,
                    selected_damage,
                )


class ScytheStrikeTests(unittest.TestCase):

    def setUp(self):
        self.module = load_card("58028")
        self.ability = self.module.GetAbilities()[0]

    def test_deals_exactly_two_indirect_damage_without_grim_reaper(self):
        effect = Mock()
        treachery = Mock()
        player = Mock()
        identity = Mock()
        message = Mock()
        effect.this.CastTo.return_value = treachery
        message.GetToPlayer.return_value = player
        player.GetIdentity.return_value = identity

        with patch.object(
            self.module.Worlds,
            "FindCardOnField",
            return_value=None,
        ):
            self.ability.operation(effect, message)

        identity.TakeIndirectDamage.assert_called_once_with(
            treachery,
            2,
            effect,
        )

    def test_grim_reaper_activates_instead_of_dealing_indirect_damage(self):
        effect = Mock()
        player = Mock()
        identity = Mock()
        message = Mock()
        grim_reaper = Mock()
        minion = Mock()
        message.GetToPlayer.return_value = player
        player.GetIdentity.return_value = identity
        grim_reaper.CastTo.return_value = minion

        with patch.object(
            self.module.Worlds,
            "FindCardOnField",
            return_value=grim_reaper,
        ):
            self.ability.operation(effect, message)

        minion.DoActivate.assert_called_once_with(player, effect)
        identity.TakeIndirectDamage.assert_not_called()


class IndirectDamageSystemTests(unittest.TestCase):

    @staticmethod
    def assign(selected_targets, available_targets, damage=2):
        action = Mock()
        player = Mock()
        action.GetPlayer.return_value = player
        player.ChooseAbilities.return_value = [
            SimpleNamespace(targets=selected_targets)
        ]
        source = Mock()
        effect = Mock()

        messages = PlayerAction.AssignDamage(
            action,
            available_targets,
            source,
            damage,
            effect,
        )
        choice = player.ChooseAbilities.call_args.args[1]
        return messages, choice, source, effect

    def test_repeated_identity_selection_assigns_both_damage(self):
        identity = Mock()
        took_damage = Mock()
        identity.TakeDamage.return_value = took_damage

        messages, choice, source, effect = self.assign(
            [identity, identity],
            [identity],
        )

        identity.TakeDamage.assert_called_once()
        args = identity.TakeDamage.call_args.args
        self.assertIs(args[0], source)
        self.assertEqual(args[1].damage, 2)
        self.assertTrue(args[1].is_indirect_damage)
        self.assertIs(args[2], effect)
        self.assertEqual(messages, [took_damage])

        selector = choice.selectors[0]
        self.assertEqual(selector.selector_range.raw_range, ("Zero", 2))
        self.assertEqual(selector.selector_rule.repeat_rules, ["Health"])

    def test_split_assignment_deals_one_damage_to_each_character(self):
        identity = Mock()
        ally = Mock()
        identity_message = Mock()
        ally_message = Mock()
        identity.TakeDamage.return_value = identity_message
        ally.TakeDamage.return_value = ally_message

        messages, _, source, effect = self.assign(
            [identity, ally],
            [identity, ally],
        )

        for unit in (identity, ally):
            unit.TakeDamage.assert_called_once()
            args = unit.TakeDamage.call_args.args
            self.assertIs(args[0], source)
            self.assertEqual(args[1].damage, 1)
            self.assertTrue(args[1].is_indirect_damage)
            self.assertIs(args[2], effect)
        self.assertEqual(messages, [identity_message, ally_message])


class WonderManReplayTests(unittest.TestCase):

    def test_legacy_saved_rhino_replay_is_rejected(self):
        configured = os.environ.get("WONDER_MAN_REPLAY")
        if configured:
            replay = Path(configured)
        else:
            candidates = sorted(
                (ROOT / "replays").glob("*wonder_man-rhino-*.json"),
                key=lambda path: path.stat().st_mtime,
            )
            if not candidates:
                self.skipTest(
                    "set WONDER_MAN_REPLAY or save a Wonder Man vs Rhino replay"
                )
            replay = candidates[-1]

        with replay.open(encoding='utf-8') as replay_file:
            data = json.load(replay_file)

        with self.assertRaises(UnsupportedReplayRulesError):
            LoaderHelper.EnsureSupportedReplay(Scene(rules=data.get('rules', [])))


if __name__ == "__main__":
    unittest.main()
