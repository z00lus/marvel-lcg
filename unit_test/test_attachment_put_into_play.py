from types import SimpleNamespace
import unittest
from unittest.mock import patch

# Preserve the application's normal import ordering.
from engine import Engine

from cards.database import CardsDB
from engine.lib.version import Ver
from game.card.factory import CardFactory
from game.effect.rule import GameRule
from game.message import Message
from game.scene.replay.campaign import CampaignDescriptor
from game.scene.replay.hero import HeroDescriptor
from game.scene.scene import Scene
from game.world.phase import Phase
from game.world.world import World


class AttachmentPutIntoPlayTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        Ver.Initialize()
        if not CardsDB.papers:
            CardsDB.Initialize()

    def MakeWorld(self):
        manager = SimpleNamespace(skip=SimpleNamespace(is_skipping=True))
        scene = Scene(
            version=str(Ver.version),
            rules=["v18_all"],
            campaign=CampaignDescriptor(campaign_id="rhino", name="Rhino"),
            players=[HeroDescriptor(
                version="",
                name="Cable",
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
            "40001a,40001b",
            world.players[0].area_hero,
            world,
            ui_render=False,
        ).face
        identity.ResetHealth(GameRule(identity))
        world.phase.SetState(Phase.State.PlayerTurn)
        world.current_player = world.players[0]
        return world, world.players[0]

    def ResolveLockAndLoad(self, world, player, sidearm):
        scheme = CardFactory.GenerateCard(
            "40019",
            world.area_schemes_side,
            world,
            ui_render=False,
        ).face
        effect = next(
            candidate for candidate in scheme.effect.GetAll()
            if candidate.ability.when is Message.WhenSchemeBeDefeated
        )
        effect.context.initiator = player

        def choose_sidearm(selector, search_effect):
            legal_targets = list(selector.GetAllLegalTargets(search_effect))
            self.assertIn(sidearm, legal_targets)
            target_range = selector.GetTargetRange(search_effect, legal_targets)
            self.assertIsNotNone(target_range)
            self.assertTrue(selector.AfterSelectTargets(
                search_effect,
                [sidearm],
                target_range,
            ))
            return [sidearm]

        with patch.object(player, "AskChooseSelect", side_effect=choose_sidearm):
            controller_manager = SimpleNamespace(
                console=SimpleNamespace(TryBreak=lambda check_world: None),
            )
            with patch.object(
                Engine,
                "game",
                SimpleNamespace(controller_manager=controller_manager),
                create=True,
            ):
                effect.ability.operation(effect, object())

    def test_lock_and_load_keeps_sidearm_in_deck_without_a_legal_ally(self):
        world, player = self.MakeWorld()
        CardFactory.GenerateCard(
            "01088",
            player.player_deck,
            world,
            ui_render=False,
        )
        sidearm = CardFactory.GenerateCard(
            "40030",
            player.player_deck,
            world,
            ui_render=False,
        ).face

        self.ResolveLockAndLoad(world, player, sidearm)

        self.assertIs(sidearm.card.area, player.player_deck)
        self.assertFalse(sidearm.IsInPlay())
        self.assertFalse(sidearm.card.state.is_attached)
        self.assertNotIn(sidearm, player.area_processing.Get())

    def test_lock_and_load_attaches_sidearm_when_an_ally_is_legal(self):
        world, player = self.MakeWorld()
        ally = CardFactory.GenerateCard(
            "40024",
            player.allies,
            world,
            ui_render=False,
        ).face
        CardFactory.GenerateCard(
            "01088",
            player.player_deck,
            world,
            ui_render=False,
        )
        sidearm = CardFactory.GenerateCard(
            "40030",
            player.player_deck,
            world,
            ui_render=False,
        ).face

        self.ResolveLockAndLoad(world, player, sidearm)

        self.assertIs(sidearm.GetBindFace(), ally)
        self.assertIs(sidearm.card.area, ally.GetInventoryDeck())
        self.assertTrue(sidearm.IsInPlay())
        self.assertTrue(sidearm.card.state.is_attached)
        self.assertNotIn(sidearm, player.area_processing.Get())

    def test_specialized_training_puts_chosen_linked_upgrade_into_play(self):
        world, player = self.MakeWorld()
        identity = player.GetIdentity()
        scheme = CardFactory.GenerateCard(
            "43021",
            world.area_schemes_side,
            world,
            ui_render=False,
        ).face
        front_line_specialist = next(
            face for face in world.aside_deck.Get()
            if face.paper.card_id == "43036"
        )
        effect = next(
            candidate for candidate in scheme.effect.GetAll()
            if candidate.ability.when is Message.WhenSchemeBeDefeated
        )
        effect.context.initiator = player

        def choose_specialization(selector, search_effect):
            legal_targets = list(selector.GetAllLegalTargets(search_effect))
            self.assertIn(front_line_specialist, legal_targets)
            target_range = selector.GetTargetRange(search_effect, legal_targets)
            self.assertIsNotNone(target_range)
            self.assertTrue(selector.AfterSelectTargets(
                search_effect,
                [front_line_specialist],
                target_range,
            ))
            return [front_line_specialist]

        controller_manager = SimpleNamespace(
            console=SimpleNamespace(TryBreak=lambda check_world: None),
        )
        with patch.object(
            player,
            "AskChooseSelect",
            side_effect=choose_specialization,
        ), patch.object(
            Engine,
            "game",
            SimpleNamespace(controller_manager=controller_manager),
            create=True,
        ):
            effect.ability.operation(effect, object())

        self.assertTrue(front_line_specialist.card.state.is_attached)
        self.assertIs(front_line_specialist.GetBindFace(), identity)
        self.assertIs(
            front_line_specialist.card.area,
            identity.GetInventoryDeck(),
        )
        self.assertTrue(front_line_specialist.IsInPlay())
        self.assertNotIn(front_line_specialist, world.aside_deck.Get())


if __name__ == "__main__":
    unittest.main()
