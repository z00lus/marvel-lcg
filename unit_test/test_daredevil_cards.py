from __future__ import annotations

import importlib
import json
from pathlib import Path
from unittest import TestCase
from unittest.mock import Mock, patch

# Match the application's import order without initializing the server.
from engine import Engine
from build import Build
from cards.database import CardsDB
from engine.lib.version import Ver
from game.card.factory import CardFactory


ROOT = Path(__file__).resolve().parents[1]
daredevil_pack = importlib.import_module("cards.pack.fne.daredevil")


class DaredevilScriptLoadTests(TestCase):

    def test_every_daredevil_script_builds_its_abilities(self):
        modules = [
            "cards.pack.fne.daredevil.60001a",
            "cards.pack.fne.daredevil.60001b",
            *(f"cards.pack.fne.daredevil.{card_id}" for card_id in range(60002, 60019)),
            "cards.pack.fne.daredevil.60032",
            *(f"cards.pack.fne.{card_id}" for card_id in range(60019, 60032)),
            *(f"cards.pack.fne.daredevil_nemesis.{card_id}" for card_id in range(60033, 60037)),
        ]

        for module_name in modules:
            with self.subTest(module=module_name):
                abilities = importlib.import_module(module_name).GetAbilities()
                self.assertTrue(abilities)

    def test_every_daredevil_card_face_can_be_created(self):
        Ver.Initialize()
        if not CardsDB.papers:
            CardsDB.Initialize()

        world = Mock()
        world.GetPlayerNumIcon.return_value = 1
        card_ids = [
            "60001a",
            "60001b",
            *(f"{card_id}" for card_id in range(60002, 60037)),
        ]

        with patch.object(Build, "release", False):
            for card_id in card_ids:
                with self.subTest(card_id=card_id):
                    paper = CardsDB.FindCardPaper(card_id)
                    face = CardFactory.CreateFace(paper, world)
                    self.assertEqual(face.paper.card_id, card_id)

    def test_starter_deck_has_legal_preconstructed_counts(self):
        with (ROOT / "deck/starter/daredevil.json").open(encoding="utf-8") as source:
            deck = json.load(source)

        self.assertEqual(len(deck["hero_deck"]), 15)
        self.assertEqual(len(deck["player_deck"]), 25)
        self.assertEqual(len(deck["set_aside"]), 5)
        self.assertEqual(len(deck["obligations"]), 1)
        self.assertEqual(len(deck["nemesis_set"]), 5)


class SenseDeckTests(TestCase):

    def test_sense_upgrade_leaving_play_goes_to_bottom_of_sense_deck(self):
        module = importlib.import_module("cards.pack.fne.daredevil.60001b")
        ability = module.GetAbilities()[1]
        sense_deck = Mock()
        player = Mock()
        player.special_decks = {daredevil_pack.SENSE_DECK: sense_deck}
        effect = Mock()
        effect.GetInitiator.return_value = player
        sense = Mock()
        message = Mock(trigger=sense, into_area=Mock())

        with patch.object(module.Faces, "MoveAllToDeck") as move_to_deck:
            ability.operation(effect, message)

        message.SetBeInstead.assert_called_once_with(effect)
        move_to_deck.assert_called_once_with([sense], sense_deck, "Bottom", effect)

    def test_choose_sense_plays_selected_card_without_resource_cost(self):
        sense = Mock()
        sense_deck = Mock()
        sense_deck.GetAll.return_value = [sense]
        player = Mock()
        player.special_decks = {daredevil_pack.SENSE_DECK: sense_deck}
        player.MayChooseFace.return_value = sense
        player.PlayCardsLikeInTurn.return_value = [sense]
        effect = Mock()

        played = daredevil_pack.ChooseAndPlaySense(player, effect)

        self.assertIs(played, sense)
        player.PlayCardsLikeInTurn.assert_called_once_with(
            [sense],
            effect,
            ignore_resources_cost=True,
            forced=True,
            if_not_play_discard_it=False,
        )


class DaredevilAbilityTests(TestCase):

    def test_focus_the_senses_allows_both_identity_forms_to_remove_threat(self):
        module = importlib.import_module("cards.pack.fne.daredevil.60012")
        cannot_remove = module.GetAbilities()[1]
        effect = Mock()
        message = Mock()

        message.by_face.IsName.side_effect = lambda name: name == "Daredevil"
        self.assertFalse(cannot_remove.conditions[-1](effect, message))

        message.by_face.IsName.side_effect = lambda name: name == "Matt Murdock"
        self.assertFalse(cannot_remove.conditions[-1](effect, message))

        message.by_face.IsName.return_value = False
        message.by_face.IsName.side_effect = None
        self.assertTrue(cannot_remove.conditions[-1](effect, message))

    def test_stealth_training_requires_exact_side_scheme_defeat(self):
        module = importlib.import_module("cards.pack.fne.60028")
        ability = module.GetAbilities()[1]
        condition = ability.conditions[-1]
        side_scheme = Mock(spec=module.SchemeSide2)
        side_scheme.threat = 0
        property = Mock(is_divided=False)
        property.GetThwart.return_value = 3
        after = Mock(
            scheme=side_scheme,
            remove_threat=3,
            would_thw_message=Mock(property=property),
        )
        message = Mock(trigger=Mock(), after_thw_messages=[after])

        self.assertTrue(condition(Mock(), message))

        after.remove_threat = 2
        self.assertFalse(condition(Mock(), message))

    def test_cross_examination_adds_optional_damage_per_attached_upgrade(self):
        module = importlib.import_module("cards.pack.fne.daredevil.60008")
        ability = module.GetAbilities()[0]
        event = Mock()
        event.CastTo.return_value = event
        target = Mock()
        target.GetInventoryDeck.return_value.FindCards.return_value = [Mock(), Mock()]
        player = Mock()
        player.AskChooseOneText.return_value = 2
        effect = Mock(this=event, targets=[target])
        effect.GetInitiator.return_value = player

        ability.operation(effect, Mock())

        event.DealDamage.assert_called_once_with([target], 5, effect)

    def test_elektra_redirects_consequential_damage_to_daredevil(self):
        module = importlib.import_module("cards.pack.fne.daredevil.60007")
        ability = module.GetAbilities()[0]
        daredevil = Mock()
        player = Mock()
        player.GetHero.return_value = daredevil
        effect = Mock()
        effect.GetInitiator.return_value = player
        message = Mock()

        ability.operation(effect, message)

        message.ChangeDealtToTarget.assert_called_once_with(daredevil, effect)
