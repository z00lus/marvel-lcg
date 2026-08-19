from __future__ import annotations

import importlib
import inspect
import unittest
from types import SimpleNamespace
from unittest.mock import ANY, Mock, patch

from engine import Engine  # noqa: F401
from cards.database import CardsDB
from engine.lib.version import Ver
from game.ability.ability_type import AbilityType
from game.card.face import Attachment, Upgrade, Villain
from game.card.factory import CardFactory
from game.element.cost import Cost
from game.effect.rule import GameRule
from game.message import Message
from game.scene.replay.campaign import CampaignDescriptor
from game.scene.replay.hero import HeroDescriptor
from game.scene.scene import Scene
from game.world.phase import Phase
from game.world.world import World


PACKAGE = importlib.import_module("cards.pack.fne.electro")


def load_card(card_id: str):
    return importlib.import_module(f"cards.pack.fne.electro.{card_id}")


def execute_choice(ability, outer_effect):
    choice_effect = Mock()
    choice_effect.targets = []
    choice_effect.GetPaidResources.return_value = Mock()
    ability.operation(choice_effect, Mock())


class ElectroVillainTests(unittest.TestCase):

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
                campaign_id="the_getaway",
                name="The Getaway",
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

    def assert_stage_setup(self, stage_id: str, expected_charge: int):
        world, player = self.make_world()
        villain = CardFactory.GenerateCard(
            stage_id,
            world.GetScenario().area_villain,
            world,
            ui_render=False,
        ).face
        villain.SetEncounterDeck(world.GetScenario().encounter_deck)
        charge = CardFactory.GenerateCard(
            "60079",
            world.aside_deck,
            world,
            ui_render=False,
        ).face
        effect = next(
            candidate for candidate in villain.effect.GetAll()
            if candidate.ability.when is Message.WhenCardRevealed
        )
        effect.context.initiator = player
        message = Mock()
        message.GetToPlayer.return_value = player

        effect.ability.operation(effect, message)

        self.assertIs(charge.GetBindFace(), villain)
        self.assertIs(charge.card.area, villain.GetInventoryDeck())
        self.assertEqual(charge.GetCounters("charge"), expected_charge)

    def test_standard_stage_one_setup_attaches_real_electric_charge(self):
        self.assert_stage_setup("60076", 2)

    def test_expert_opening_stage_two_setup_attaches_real_electric_charge(self):
        self.assert_stage_setup("60077", 2)

    def test_stage_one_finds_attaches_and_charges_electric_charge(self):
        ability = load_card("60076").GetAbilities()[0]
        villain = Mock()
        charge = Mock()
        player = Mock()
        effect = Mock()
        effect.this.CastTo.return_value = villain
        message = Mock()
        message.GetToPlayer.return_value = player

        with (
            patch.object(PACKAGE.Find, "FindAndAttachTo", return_value=charge) as find,
            patch.object(PACKAGE.Faces, "PlaceCountersOn") as place,
        ):
            ability.operation(effect, message)

        find.assert_called_once_with(
            effect,
            villain,
            who_perform=player,
            finder=PACKAGE.ELECTRIC_CHARGE,
        )
        place.assert_called_once_with([charge], "2*", "charge", effect)

    def test_stage_three_adds_three_per_player_charge_without_refinding(self):
        module = load_card("60078")
        ability = module.GetAbilities()[0]
        charge = Mock()
        effect = Mock()

        with (
            patch.object(module, "FindElectricCharge", return_value=charge),
            patch.object(PACKAGE.Faces, "PlaceCountersOn") as place,
        ):
            ability.operation(effect, Mock())

        place.assert_called_once_with([charge], "3*", "charge", effect)

    def test_electro_scheming_adds_the_stage_specific_charge(self):
        for card_id, expected in (("60076", 1), ("60077", 1), ("60078", 2)):
            with self.subTest(card_id=card_id):
                ability = load_card(card_id).GetAbilities()[1]
                charge = Mock()
                effect = Mock()
                with (
                    patch.object(PACKAGE, "FindElectricCharge", return_value=charge),
                    patch.object(PACKAGE.Faces, "PlaceCountersOn") as place,
                ):
                    ability.operation(effect, Mock())
                place.assert_called_once_with([charge], expected, "charge", effect)


class ElectricChargeTests(unittest.TestCase):

    def test_attack_spends_charge_as_cost_and_gains_boost_and_overkill(self):
        abilities = load_card("60079").GetAbilities()
        attack = next(
            ability for ability in abilities
            if ability.when is Message.WhenUnitWouldAttack
        )
        effect = Mock()
        message = Mock()

        attack.operation(effect, message)

        self.assertEqual(len(attack.cost_funcs), 1)
        self.assertEqual(attack.cost_funcs[0].name, "charge")
        message.GiveAdditionalBoostCardForThisActivation.assert_called_once_with(
            1, effect
        )
        message.GainOverKill.assert_called_once_with(effect)

    def test_hero_action_requires_energy_or_two_resources_and_one_charge(self):
        action = next(
            ability for ability in load_card("60079").GetAbilities()
            if ability.type is AbilityType.HeroAction
        )

        cost = action.cost_fn(Mock(), [])
        self.assertEqual(cost.y, 1)
        self.assertIsNotNone(cost.rule.or_res)
        self.assertEqual(cost.rule.or_res.val, 2)
        self.assertEqual(len(action.cost_funcs), 1)
        self.assertEqual(action.cost_funcs[0].name, "charge")


class DrainedOfPowerTests(unittest.TestCase):

    def test_reveal_exhausts_each_controlled_upgrade(self):
        reveal = next(
            ability for ability in load_card("60080").GetAbilities()
            if ability.when is Message.WhenCardRevealed
        )
        upgrades = [Mock(), Mock()]
        player = Mock()
        player.GetControlUpgrade.return_value = upgrades
        message = Mock()
        message.GetToPlayer.return_value = player
        effect = Mock()

        with patch.object(PACKAGE.Faces, "ExhaustAll") as exhaust:
            reveal.operation(effect, message)

        exhaust.assert_called_once_with(upgrades, effect)

    def test_upgrade_does_not_ready_when_player_declines_payment(self):
        interrupt = next(
            ability for ability in load_card("60080").GetAbilities()
            if ability.when is Message.WhenCardWouldReady
        )
        attachment = Mock()
        player = Mock()
        player.AskSpendResources.return_value = False
        upgrade = Mock()
        upgrade.GetControlByPlayer.return_value = player
        effect = Mock()
        effect.this.CastTo.return_value = attachment
        message = Mock(trigger=upgrade)

        interrupt.operation(effect, message)

        player.AskSpendResources.assert_called_once_with(ANY, effect)
        message.SetBeInstead.assert_called_once_with(effect)

    def test_paid_ready_removes_drain_and_allows_ready(self):
        interrupt = next(
            ability for ability in load_card("60080").GetAbilities()
            if ability.when is Message.WhenCardWouldReady
        )
        attachment = Mock()
        player = Mock()
        player.AskSpendResources.return_value = True
        upgrade = Mock()
        upgrade.GetControlByPlayer.return_value = player
        effect = Mock()
        effect.this.CastTo.return_value = attachment
        message = Mock(trigger=upgrade)

        with patch.object(PACKAGE.Faces, "RemoveCountersOn") as remove:
            interrupt.operation(effect, message)

        remove.assert_called_once_with([attachment], 1, "drain", effect)
        message.SetBeInstead.assert_not_called()


class ElectroEncounterCardTests(unittest.TestCase):

    def test_whiplash_discards_one_encounter_card_and_hits_for_boost_icons(self):
        ability = load_card("60081").GetAbilities()[0]
        whiplash = Mock()
        discarded = Mock()
        attacker = Mock()
        effect = Mock()
        effect.this.CastTo.return_value = whiplash
        message = Mock(attacker=attacker)

        with (
            patch.object(PACKAGE.Worlds, "DiscardEncounterTopCard", return_value=discarded),
            patch.object(PACKAGE.FacesCounter, "CountTotalBoostIcons", return_value=3),
        ):
            ability.operation(effect, message)

        attacker.TakeDamage.assert_called_once_with(whiplash, 3, effect)
        self.assertEqual(ability.cost_funcs[0].name, "charge")

    def test_charging_up_places_three_charge_when_defeated(self):
        module = load_card("60082")
        ability = module.GetAbilities()[0]
        charge = Mock()
        effect = Mock()

        with (
            patch.object(module, "FindElectricCharge", return_value=charge),
            patch.object(PACKAGE.Faces, "PlaceCountersOn") as place,
        ):
            ability.operation(effect, Mock())

        place.assert_called_once_with([charge], 3, "charge", effect)

    def test_chain_lightning_damage_uses_and_removes_charge(self):
        module = load_card("60083")
        ability = module.GetAbilities()[0]
        character = Mock(name="Hero")
        character.name = "Hero"
        character.IsReady.return_value = True
        charge = Mock()
        charge.GetCounters.return_value = 1
        player = Mock()
        player.GetControlCharacters.return_value = [character]
        player.ChooseAbilities.side_effect = (
            lambda outer_effect, *choices: execute_choice(choices[1], outer_effect)
        )
        message = Mock()
        message.GetToPlayer.return_value = player
        treachery = Mock()
        effect = Mock()
        effect.this.CastTo.return_value = treachery

        with (
            patch.object(module, "FindElectricCharge", return_value=charge),
            patch.object(PACKAGE.Faces, "RemoveCountersOn") as remove,
        ):
            ability.operation(effect, message)

        character.TakeDamage.assert_called_once_with(treachery, 3, effect)
        remove.assert_called_once_with([charge], 1, "charge", effect)

    def test_energy_overload_surges_without_printed_energy(self):
        ability = load_card("60084").GetAbilities()[0]
        treachery = Mock()
        player = Mock()
        player.hand_cards.GetAll.return_value = []
        message = Mock()
        message.GetToPlayer.return_value = player
        effect = Mock()
        effect.this.CastTo.return_value = treachery

        ability.operation(effect, message)

        treachery.GainSurge.assert_called_once_with(1, effect)
        player.ChooseAbilities.assert_not_called()

    def test_energy_overload_offers_one_choice_for_each_energy_card(self):
        module = load_card("60084")
        ability = module.GetAbilities()[0]
        treachery = Mock()
        cards = [Mock(name="energy-1"), Mock(name="energy-2")]
        cards[0].name = "Energy One"
        cards[1].name = "Energy Two"
        player = Mock()
        player.hand_cards.GetAll.return_value = cards
        message = Mock()
        message.GetToPlayer.return_value = player
        effect = Mock()
        effect.this.CastTo.return_value = treachery

        finder = Mock()
        finder.Checks.return_value = cards
        with patch.object(module, "CardFinder", return_value=finder):
            ability.operation(effect, message)

        self.assertEqual(player.ChooseAbilities.call_count, 2)
        for call in player.ChooseAbilities.call_args_list:
            self.assertEqual(len(call.args[1:]), 2)

    def test_shocking_revelation_discards_for_each_controlled_card(self):
        module = load_card("60085")
        ability = module.GetAbilities()[0]
        controlled = [Mock(), Mock(), Mock()]
        discarded = [Mock(), Mock()]
        player = Mock()
        player.GetControlCards.return_value = controlled
        player.DiscardDeckTopCards.return_value = discarded
        message = Mock()
        message.GetToPlayer.return_value = player
        effect = Mock()
        effect.this.CastTo.return_value = Mock()

        finder = Mock()
        finder.Checks.return_value = []
        with patch.object(module, "CardFinder", return_value=finder):
            ability.operation(effect, message)

        player.DiscardDeckTopCards.assert_called_once_with(3, effect)
        player.ChooseAbilities.assert_not_called()

    def test_encounter_cards_do_not_treat_boost_use_as_reveal(self):
        for card_id in ("60080", "60083", "60084", "60085"):
            with self.subTest(card_id=card_id):
                abilities = load_card(card_id).GetAbilities()
                self.assertFalse(any(
                    ability.when is Message.WhenCardBecomeBoost
                    for ability in abilities
                ))

    def test_scripts_do_not_use_unseeded_randomness(self):
        for card_id in range(60076, 60086):
            with self.subTest(card_id=card_id):
                source = inspect.getsource(load_card(str(card_id)))
                self.assertNotIn("import random", source)
                self.assertNotIn("random.", source)


if __name__ == "__main__":
    unittest.main()
