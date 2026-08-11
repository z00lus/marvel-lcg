from types import SimpleNamespace
import unittest
from unittest.mock import patch

# Preserve the application's normal import ordering.
from engine import Engine

from cards.database import CardsDB
from engine.lib.version import Ver
from game.card.factory import CardFactory
from game.element.resources import Resources
from game.effect.effect import Effect
from game.effect.rule import GameRule
from game.event.manager import EventManager
from game.message import Message
from game.scene.replay.campaign import CampaignDescriptor
from game.scene.replay.hero import HeroDescriptor
from game.scene.scene import Scene
from game.world.phase import Phase
from game.world.world import World


class RealCardActivationRegressionTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        Ver.Initialize()
        if not CardsDB.papers:
            CardsDB.Initialize()

    def MakeWorld(
        self,
        *,
        hero_name="Spider-Man",
        identity_card_id="01001a,01001b",
    ):
        manager = SimpleNamespace(skip=SimpleNamespace(is_skipping=True))
        scene = Scene(
            version=str(Ver.version),
            rules=["v18_all"],
            campaign=CampaignDescriptor(campaign_id="rhino", name="Rhino"),
            players=[HeroDescriptor(
                version="",
                name=hero_name,
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
            identity_card_id,
            world.players[0].area_hero,
            world,
            ui_render=False,
        ).face
        identity.ResetHealth(GameRule(identity))
        world.phase.SetState(Phase.State.PlayerTurn)
        world.current_player = world.players[0]
        return world, world.players[0], identity

    def test_helicarrier_resolves_through_real_world_and_cannot_repeat_exhausted(self):
        world, player, identity = self.MakeWorld()
        helicarrier = CardFactory.GenerateCard(
            "01092",
            player.supports,
            world,
            ui_render=False,
        ).face
        effect = next(
            candidate for candidate in helicarrier.effect.global_effects
            if candidate.ability.flags.is_action
        )
        message = Message.WhenPlayerInTurn(player, 1)
        available = EventManager.FilterAvailableEffects(
            message,
            [effect],
            player,
            world,
            None,
        )
        self.assertEqual(available, [effect])
        self.assertEqual(effect.context.all_legal_targets, [identity])

        effect.context.targets_internal = [identity]
        controller_manager = SimpleNamespace(
            console=SimpleNamespace(TryBreak=lambda check_world: None),
        )
        with patch.object(
            player,
            "AskChooseFaces",
            return_value=[helicarrier],
        ), patch.object(
            Engine,
            "game",
            SimpleNamespace(controller_manager=controller_manager),
            create=True,
        ):
            self.assertTrue(effect.checker.CheckBeforeActive(player))
            self.assertTrue(effect.ResolveSelf(message, effect))

        self.assertFalse(helicarrier.card.IsReady())
        second_message = Message.WhenPlayerInTurn(player, 1)
        self.assertEqual(
            EventManager.FilterAvailableEffects(
                second_message,
                [effect],
                player,
                world,
                None,
            ),
            [],
        )

    def test_helicarrier_reduces_next_playable_one_cost_card_to_zero(self):
        world, player, identity = self.MakeWorld()
        helicarrier = CardFactory.GenerateCard(
            "01092",
            player.supports,
            world,
            ui_render=False,
        ).face
        interrogation_room = CardFactory.GenerateCard(
            "01063",
            player.hand_cards,
            world,
            ui_render=False,
        ).face
        helicarrier_effect = next(
            candidate for candidate in helicarrier.effect.global_effects
            if candidate.ability.flags.is_action
        )
        message = Message.WhenPlayerInTurn(player, 1)
        controller_manager = SimpleNamespace(
            console=SimpleNamespace(TryBreak=lambda check_world: None),
        )

        with patch.object(
            player,
            "AskChooseFaces",
            return_value=[helicarrier],
        ), patch.object(
            Engine,
            "game",
            SimpleNamespace(controller_manager=controller_manager),
            create=True,
        ):
            available = EventManager.FilterAvailableEffects(
                message,
                [helicarrier_effect],
                player,
                world,
                None,
            )
            self.assertEqual(available, [helicarrier_effect])
            helicarrier_effect.context.targets_internal = [identity]
            self.assertTrue(helicarrier_effect.checker.CheckBeforeActive(player))
            self.assertTrue(helicarrier_effect.ResolveSelf(
                message,
                helicarrier_effect,
            ))

            play_effect = next(
                candidate for candidate in interrogation_room.effect.global_effects
                if candidate.ability.is_play
            )
            available = EventManager.FilterAvailableEffects(
                message,
                [play_effect],
                player,
                world,
                None,
            )

        self.assertEqual(available, [play_effect])
        self.assertEqual(
            play_effect.checker.cost_for_different_target.GetCost(None).val,
            0,
        )

    def test_interception_imminent_exhausts_milano_and_removes_threat(self):
        world, player, _ = self.MakeWorld()
        scheme = CardFactory.GenerateCard(
            "16106b",
            world.area_schemes_main,
            world,
            ui_render=False,
        ).face
        milano = CardFactory.GenerateCard(
            "16142",
            player.supports,
            world,
            ui_render=False,
        ).face
        scheme.SetTokens(5, "threat", GameRule(scheme))
        effect = next(
            candidate for candidate in scheme.effect.global_effects
            if candidate.ability.flags.is_action
        )
        message = Message.WhenPlayerInTurn(player, 1)
        available = EventManager.FilterAvailableEffects(
            message,
            [effect],
            player,
            world,
            None,
        )
        self.assertEqual(available, [effect])
        self.assertEqual(effect.context.all_legal_targets, [scheme])
        effect.context.targets_internal = [scheme]

        controller_manager = SimpleNamespace(
            console=SimpleNamespace(TryBreak=lambda check_world: None),
        )
        with patch.object(
            player,
            "AskChooseFaces",
            return_value=[milano],
        ), patch.object(
            Engine,
            "game",
            SimpleNamespace(controller_manager=controller_manager),
            create=True,
        ):
            self.assertTrue(effect.checker.CheckBeforeActive(player))
            self.assertTrue(effect.ResolveSelf(message, effect))

        self.assertFalse(milano.card.IsReady())
        self.assertEqual(scheme.threat, 2)
        self.assertIs(milano.card.GetOwner(), player)
        self.assertIs(milano.GetControlBy(), player)

    def test_star_lord_discount_pays_for_declared_player_card_only(self):
        world, player, identity = self.MakeWorld(
            hero_name="Star-Lord",
            identity_card_id="17001a,17001b",
        )
        encounter_card = CardFactory.GenerateCard(
            "01186",
            world.GetScenario().encounter_deck,
            world,
            ui_render=False,
        ).face
        helicarrier = CardFactory.GenerateCard(
            "01092",
            player.hand_cards,
            world,
            ui_render=False,
        ).face
        play_effect = next(
            candidate for candidate in helicarrier.effect.global_effects
            if candidate.ability.is_play
        )
        message = Message.WhenPlayerInTurn(player, 1)
        controller_manager = SimpleNamespace(
            console=SimpleNamespace(TryBreak=lambda check_world: None),
        )
        with patch.object(
            player,
            "AskChooseFaces",
            side_effect=lambda targets, *args, **kwargs: list(targets),
        ), patch.object(
            Engine,
            "game",
            SimpleNamespace(controller_manager=controller_manager),
            create=True,
        ):
            available = EventManager.FilterAvailableEffects(
                message,
                [play_effect],
                player,
                world,
                None,
            )
            self.assertEqual(available, [play_effect])
            play_effect.context.targets_internal = \
                play_effect.context.all_legal_targets[:1]
            payment = play_effect.checker.cost_for_different_target.GetPayment(None)
            discount_effects = [
                payment_effect
                for payment_option in payment.payments
                for payment_effect, resources in payment_option.items()
                if Resources.FromText(resources).reduce == 3
            ]
            self.assertEqual(len(discount_effects), 1)
            self.assertIs(discount_effects[0].this, identity)
            discount_effects[0].context.initiator = player
            self.assertTrue(discount_effects[0].PrepareSelfCosts())
            discount_effects[0].ClearPreparedSelfCosts()
            play_effect.context.paid_this_res_effects = discount_effects
            self.assertTrue(player.ResolveEffect(play_effect, message))

        self.assertIs(helicarrier.card.area, player.supports)
        self.assertIs(encounter_card.card.area, player.dealt_encounter_cards)
        self.assertFalse(world.stat.IsOncePerRound(
            discount_effects[0].ability,
        ))

    def AssertEncounterAttachmentCanBePaidAndDiscarded(
        self,
        card_id,
        resource_card_ids,
        *,
        alter_ego=False,
    ):
        world, player, identity = self.MakeWorld()
        if alter_ego:
            identity.card.Flip(GameRule(identity))
            identity = identity.card.face
        attachment = CardFactory.GenerateCard(
            card_id,
            world.area_processing,
            world,
            ui_render=False,
        ).face
        self.assertTrue(attachment.AttachTo2(identity, GameRule(attachment)))
        for resource_card_id in resource_card_ids:
            CardFactory.GenerateCard(
                resource_card_id,
                player.hand_cards,
                world,
                ui_render=False,
            )

        effect = next(
            candidate for candidate in attachment.effect.global_effects
            if candidate.ability.flags.is_action
        )
        message = Message.WhenPlayerInTurn(player, 1)
        controller_manager = SimpleNamespace(
            console=SimpleNamespace(TryBreak=lambda check_world: None),
        )
        with patch.object(
            player,
            "AskChooseFaces",
            side_effect=lambda targets, *args, **kwargs: list(targets),
        ), patch.object(
            Engine,
            "game",
            SimpleNamespace(controller_manager=controller_manager),
            create=True,
        ):
            available = EventManager.FilterAvailableEffects(
                message,
                [effect],
                player,
                world,
                None,
            )
            self.assertEqual(available, [effect])
            payment = effect.checker.cost_for_different_target.GetPayment(None)
            self.assertTrue(effect.checker.cost_for_different_target.HasPayableTarget())
            effect.context.paid_this_res_effects = [
                next(iter(payment_option))
                for payment_option in payment.payments
            ]
            self.assertTrue(effect.checker.CheckBeforeActive(player))
            self.assertTrue(effect.ResolveSelf(message, effect))

        self.assertIs(
            attachment.card.area,
            world.GetScenario().encounter_discard_pile,
        )
        self.assertEqual(player.hand_cards.GetSize(), 0)
        self.assertEqual(player.discard_pile.GetSize(), len(resource_card_ids))

    def test_restrained_real_world_action_pays_energy_physical_and_discards(self):
        self.AssertEncounterAttachmentCanBePaidAndDiscarded(
            "21083",
            ("01085", "01083"),
        )

    def test_seduced_real_world_action_pays_energy_mental_and_discards(self):
        self.AssertEncounterAttachmentCanBePaidAndDiscarded(
            "21179",
            ("01085", "01086"),
            alter_ego=True,
        )

    def test_for_justice_without_a_scheme_fails_before_any_cost_is_prepared(self):
        world, player, _ = self.MakeWorld()
        event = CardFactory.GenerateCard(
            "01060",
            player.hand_cards,
            world,
            ui_render=False,
        ).face
        effect = next(
            candidate for candidate in event.effect.global_effects
            if candidate.ability.is_play
        )
        hand_size = player.hand_cards.GetSize()
        discard_size = player.discard_pile.GetSize()
        message = Message.WhenPlayerInTurn(player, 1)

        available = EventManager.FilterAvailableEffects(
            message,
            [effect],
            player,
            world,
            None,
        )

        self.assertEqual(available, [])
        self.assertIs(event.card.area, player.hand_cards)
        self.assertEqual(player.hand_cards.GetSize(), hand_size)
        self.assertEqual(player.discard_pile.GetSize(), discard_size)
        self.assertEqual(world.area_processing.GetSize(), 0)
        self.assertEqual(world.stat.once_per_game_effects, [])

    def test_resolved_choice_keeps_mulligan_faces_until_the_caller_discards_them(self):
        world, player, identity = self.MakeWorld()
        selected = CardFactory.GenerateCard(
            "01060",
            player.hand_cards,
            world,
            ui_render=False,
        ).face
        kept = CardFactory.GenerateCard(
            "01061",
            player.hand_cards,
            world,
            ui_render=False,
        ).face

        def resolve_choice(by_effect, *abilities, **kwargs):
            choice = Effect(identity, abilities[0], world=world)
            choice.context.targets_internal = [selected]
            # Choice callers read effect.targets after the choice effect has
            # completed its normal operation cleanup.
            choice.context.ResetAfterOperation()
            return [choice]

        with patch.object(player, "ChooseAbilities", side_effect=resolve_choice):
            discarded = player.AskDiscardFaces(
                player.hand_cards.Get(),
                (0, "All"),
                GameRule(identity),
            )

        self.assertEqual(discarded, [selected])
        self.assertIs(selected.card.area, player.discard_pile)
        self.assertIs(kept.card.area, player.hand_cards)

    def test_avengers_mansion_play_pays_with_normal_discard_resource_choices(self):
        world, player, identity = self.MakeWorld()
        mansion = CardFactory.GenerateCard(
            "01091",
            player.hand_cards,
            world,
            ui_render=False,
        ).face
        resource_faces = [
            CardFactory.GenerateCard(
                card_id,
                player.hand_cards,
                world,
                ui_render=False,
            ).face
            for card_id in ("01060", "01061", "01063", "01093")
        ]
        play_effect = next(
            candidate for candidate in mansion.effect.global_effects
            if candidate.ability.is_play
        )
        message = Message.WhenPlayerInTurn(player, 1)
        controller_manager = SimpleNamespace(
            console=SimpleNamespace(TryBreak=lambda check_world: None),
        )

        def resolve_cost_target(by_effect, *abilities, **kwargs):
            choice = Effect(identity, abilities[0], world=world)
            choice.context.targets_internal = [by_effect.this]
            choice.context.ResetAfterOperation()
            return [choice]

        with patch.object(
            player,
            "ChooseAbilities",
            side_effect=resolve_cost_target,
        ), patch.object(
            Engine,
            "game",
            SimpleNamespace(controller_manager=controller_manager),
            create=True,
        ):
            available = EventManager.FilterAvailableEffects(
                message,
                [play_effect],
                player,
                world,
                None,
            )
            self.assertEqual(available, [play_effect])
            play_effect.context.targets_internal = \
                play_effect.context.all_legal_targets[:1]
            play_effect.context.paid_this_res_effects = [
                face.effect.Find(func_name="DiscardPay")[0]
                for face in resource_faces
            ]

            self.assertTrue(player.ResolveEffect(play_effect, message))

        self.assertIs(mansion.card.area, player.supports)
        self.assertEqual(player.hand_cards.GetSize(), 0)
        self.assertEqual(
            set(player.discard_pile.Get()),
            set(resource_faces),
        )


if __name__ == "__main__":
    unittest.main()
