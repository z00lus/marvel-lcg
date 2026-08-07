from types import SimpleNamespace
import unittest
from unittest.mock import Mock
from unittest.mock import patch

# Match the application's normal import order without initializing the server.
from engine import Engine

from game.ability.cost_func import CostFunc
from game.ability.ability import Ability
from game.effect.effect import Effect
from game.effect.effect_invoke import EffectInvoker
from game.effect.effect_checker import EffectChecker
from game.effect.effect_target_cost import TargetCost
from game.element.cost import Cost
from game.element.resources import Resources
from game.message.message_type import InActivationMessage
from game.card.face.base.enemy import Enemy
from game.player import Player
from game.ability.factory.additional_cost import CostFunction
from game.event.manager import EventManager
from game.player.action.player_action import PlayerAction
from game.message import Message
from game.ability.ability_type import TimingPriority
from cards.database import CardsDB
from engine.lib.version import Ver
from game.card.factory import CardFactory


class V17SimultaneousResourceCostTests(unittest.TestCase):

    def test_double_resource_can_be_divided_between_two_costs(self):
        allocations = Resources.FindCostAllocations(
            Resources("YY"),
            [Cost("1"), Cost("Y")],
        )

        self.assertEqual(len(allocations), 1)
        self.assertEqual(allocations[0][0].text_legacy, "Y")
        self.assertEqual(allocations[0][1].text_legacy, "Y")

    def test_player_has_a_choice_when_more_than_one_split_is_legal(self):
        allocations = Resources.FindCostAllocations(
            Resources("YYY"),
            [Cost("1"), Cost("Y")],
        )

        paid_values = {(allocation[0].val, allocation[1].val) for allocation in allocations}
        self.assertEqual(paid_values, {(1, 2), (2, 1)})

    def test_each_component_cost_keeps_its_own_resource_rule(self):
        allocations = Resources.FindCostAllocations(
            Resources("RBY"),
            [Cost("1"), Cost("2", same_type=True)],
        )

        self.assertEqual(allocations, [])

    def test_spend_only_cost_cannot_assign_resources_to_zero_base_cost(self):
        allocations = Resources.FindCostAllocations(
            Resources("Y"),
            [Cost("0", up_to=True), Cost("Y")],
        )

        self.assertEqual(len(allocations), 1)
        self.assertEqual(allocations[0][0].val, 0)
        self.assertEqual(allocations[0][1].text_legacy, "Y")

    def test_payability_check_uses_component_costs(self):
        target_cost = TargetCost()
        target_cost.AddTarget(
            None,
            Cost("1") + Cost("Y"),
            component_costs=[Cost("1"), Cost("Y")],
        )
        target_cost.AddPayment(None, object(), Resources("YY"), object())

        self.assertTrue(target_cost.HasPayableTarget())

    def test_selected_split_is_reused_by_spend_cost(self):
        spend = CostFunc.Spend(Cost("Y"))
        spend.SetSimultaneousPayment(Resources("Y"))
        player = Mock()

        self.assertTrue(spend.call_fn([], SimpleNamespace(), player))
        player.AskSpendResourcesInternal.assert_not_called()
        self.assertEqual(spend.return_res.text_legacy, "Y")

    def test_checker_assigns_the_selected_additional_cost_share(self):
        spend = CostFunc.Spend(Cost("Y"))
        payment_effect = object()
        payment = TargetCost.Payment(
            Cost("1") + Cost("Y"),
            [Cost("1"), Cost("Y")],
            [{payment_effect: "YY"}],
            {payment_effect: object()},
        )
        target_cost = TargetCost()
        target_cost.SetNoneTargetOnly()
        target_cost.target_cost[None] = payment

        context = SimpleNamespace(
            ignore_resource_cost=False,
            paid_this_res_effects=[payment_effect],
            paid_this_cost=Cost("0"),
            paid_this_resources=Resources("0"),
            this_effect_need_cost=None,
            targets_internal=[],
        )
        effect = SimpleNamespace(
            targets=[],
            context=context,
            cost_func=SimpleNamespace(GetAll=lambda: [spend]),
            world=SimpleNamespace(
                rule=SimpleNamespace(v17_actions_activations_costs=True),
            ),
        )
        checker = EffectChecker.__new__(EffectChecker)
        checker.effect = effect
        checker.ability = SimpleNamespace(selectors=[])
        checker.cost_for_different_target = target_cost
        player = Mock()
        player.SpendResource.return_value = Resources("YY")
        player.AskChooseResourceAllocation.return_value = [Resources("Y"), Resources("Y")]

        self.assertTrue(checker.CheckBeforeActive(player))
        self.assertEqual(spend.return_res.text_legacy, "Y")
        self.assertTrue(spend.simultaneous_payment)


class V17ActionCostEligibilityTests(unittest.TestCase):

    def test_printed_x_metadata_is_preserved_on_real_card_faces(self):
        Ver.Initialize()
        if not CardsDB.papers:
            CardsDB.Initialize()
        world = Mock()
        world.GetPlayerNumIcon.return_value = 1

        for card_id in ["14006", "22010", "58018"]:
            with self.subTest(card_id=card_id):
                face = CardFactory.CreateFace(CardsDB.FindCardPaper(card_id), world)
                self.assertTrue(face.printed_cost_is_x)
                self.assertEqual(face.printed_cost.val, 0)

    def MakeChecker(self, *, v17: bool, forced_action: bool) -> EffectChecker:
        effect = SimpleNamespace(
            bind_message=None,
            world=SimpleNamespace(
                rule=SimpleNamespace(
                    v17_choice=False,
                    v17_actions_activations_costs=v17,
                ),
            ),
        )
        checker = EffectChecker.__new__(EffectChecker)
        checker.effect = effect
        checker.ability = SimpleNamespace(
            flags=SimpleNamespace(is_forced_action=forced_action),
        )
        return checker

    def test_v17_forced_action_requires_a_payable_resource_cost(self):
        checker = self.MakeChecker(v17=True, forced_action=True)

        self.assertTrue(checker.RequiresPayableResourceCost())

    def test_ordinary_action_does_not_become_mandatory(self):
        checker = self.MakeChecker(v17=True, forced_action=False)

        self.assertFalse(checker.RequiresPayableResourceCost())

    def test_ignored_resource_cost_records_zero_paid(self):
        context = SimpleNamespace(
            ignore_resource_cost=True,
            paid_this_resources=Resources("Y"),
            targets_internal=[],
        )
        checker = EffectChecker.__new__(EffectChecker)
        checker.effect = SimpleNamespace(context=context, targets=[])
        checker.ability = SimpleNamespace(selectors=[])
        checker.cost_for_different_target = TargetCost()
        player = Mock()

        self.assertTrue(checker.CheckBeforeActive(player))
        self.assertEqual(context.paid_this_resources.val, 0)
        player.SpendResource.assert_not_called()

    def test_cost_selector_accepts_a_friendly_target_not_controlled_by_payer(self):
        friendly_target = Mock()
        friendly_target.IsInDeck.return_value = False
        selector = Mock()
        selector.GetAllLegalTargets.return_value = [friendly_target]
        selector.GetTargetRange.return_value = (1, 1)
        selector.AfterSelectTargets.return_value = True
        selector.selector_rule.random = False
        paid_targets = []
        cost_func = CostFunc.Base(
            selector,
            lambda targets, effect, player: paid_targets.extend(targets) or True,
        )
        player = object.__new__(Player)
        player.AskChooseFaces = Mock(return_value=[friendly_target])
        effect = SimpleNamespace(
            ability=SimpleNamespace(
                flags=SimpleNamespace(is_check_pay=False),
            ),
        )

        self.assertTrue(cost_func.PayCost(effect, player))
        self.assertEqual(paid_targets, [friendly_target])

    def test_printed_x_is_fixed_before_cost_modifiers(self):
        ability = object.__new__(Ability)
        ability.flags = SimpleNamespace(is_delay_ability=False)
        ability.play_cost = Cost("0")
        ability.play_cost_is_x = True
        ability.cost_fn = None
        effect = SimpleNamespace(
            context=SimpleNamespace(chosen_cost_x=3),
        )

        self.assertEqual(Ability.GetCost(ability, effect, []).val, 3)

    def test_get_cost_x_returns_the_declared_value_under_v17(self):
        effect = SimpleNamespace(
            world=SimpleNamespace(
                rule=SimpleNamespace(v17_actions_activations_costs=True),
            ),
            ability=SimpleNamespace(
                play_cost_is_x=True,
                cost_fn=None,
            ),
            context=SimpleNamespace(
                chosen_cost_x=2,
                paid_this_resources=Resources("YY"),
                paid_this_cost=Cost("2"),
            ),
        )

        self.assertEqual(Effect.GetCostX(effect), 2)

    def test_explicit_cost_function_keeps_overpayment_semantics(self):
        checker = self.MakeChecker(v17=True, forced_action=False)
        checker.ability.play_cost_is_x = True
        checker.ability.cost_fn = Mock()

        self.assertFalse(checker.HasDynamicPrintedXCost())


class V17ActivationAndReadyTests(unittest.TestCase):

    def test_activation_started_during_an_activation_is_deferred(self):
        activate_message = SimpleNamespace(is_be_instead=False)
        bind_message = object.__new__(InActivationMessage)
        bind_message.activate_message = activate_message
        by_effect = SimpleNamespace(
            bind_message=bind_message,
            this=SimpleNamespace(),
        )
        enemy = SimpleNamespace()
        player = Mock()

        with patch("game.operate.run_at.RunAt.AfterEnemyActivationEnd") as defer:
            result = Enemy.DoAttackYou(enemy, player, by_effect)

        self.assertIsNone(result)
        defer.assert_called_once()

    def test_declining_an_additional_ready_cost_replaces_the_ready(self):
        player = object.__new__(Player)
        trigger = Mock()
        trigger.GetControlBy.return_value = player
        trigger.GetControlByPlayer.return_value = player
        cost_func = Mock()
        cost_func.PayCost.return_value = False
        message = Mock()
        effect = Mock()

        CostFunction(effect, trigger, message, cost_func)

        cost_func.PayCost.assert_called_once_with(effect, player)
        message.SetBeInstead.assert_called_once_with(effect)

    def test_cost_and_its_responses_finish_before_post_arrow_effect(self):
        order = []

        class Trigger:
            send_resolve_message = False

        ability = SimpleNamespace(
            when=Trigger,
            operation=lambda effect, message: order.append("post-arrow"),
            flags=SimpleNamespace(
                is_check_pay=False,
                is_delay_ability=False,
                is_statistics=False,
                is_interrupt=False,
                is_response=False,
                is_resource=False,
                is_when_completed=False,
                is_when_reveal=False,
                is_when_defeated=False,
                is_setup=False,
                is_boost=False,
                is_special=False,
                is_action=False,
            ),
            is_label_defense=False,
        )
        context = SimpleNamespace(
            ResetBeforeOperation=lambda: None,
            ResetAfterOperation=lambda: None,
            end_attack_messages=[],
            end_thwart_messages=[],
        )
        this = SimpleNamespace(GetControlBy=lambda: None)
        effect = SimpleNamespace(
            ability=ability,
            initiator=SimpleNamespace(),
            world=SimpleNamespace(is_game_over=False),
            this=this,
            ProcessSelfCost=lambda: order.extend(["cost", "cost response"]) or True,
            is_unregister_after_exec=False,
            context=context,
            cost_func=SimpleNamespace(GetAll=lambda: [], Reset=lambda: None),
        )

        engine_game = SimpleNamespace(
            controller_manager=SimpleNamespace(
                console=SimpleNamespace(TryBreak=lambda world: None),
            ),
        )
        with patch.object(Engine, "game", engine_game, create=True):
            EffectInvoker.ResolveSelfInternal(effect, Trigger(), None, effect)

        self.assertEqual(order, ["cost", "cost response", "post-arrow"])

    def test_trigger_window_stays_closed_after_player_passes(self):
        effect = SimpleNamespace(
            object_id=1,
            ability=SimpleNamespace(
                flags=SimpleNamespace(is_forced_action=False),
            ),
        )
        player = Mock()
        player.ChoiceAndSpellEffect.return_value = (None, False)
        world = SimpleNamespace(
            const_players=[player],
            is_game_over=False,
        )
        manager = EventManager.__new__(EventManager)
        manager.world = world
        manager.new_effect_created = False
        message = SimpleNamespace(world=world)

        with patch.object(EventManager, "FilterAvailableEffects", return_value=[effect]) as available, \
            patch("game.event.manager.JobManager.Simultaneous", side_effect=lambda fn, players: [fn(p) for p in players]):
            manager.ProcessOptionalEffect(
                message,
                [effect],
                [],
                TimingPriority.Response,
            )

        available.assert_called_once()
        player.ChoiceAndSpellEffect.assert_called_once()

    def test_alliance_contributor_does_not_replace_card_resolver(self):
        resolver = object()
        contributor = SimpleNamespace(
            res_pool=SimpleNamespace(
                Get=lambda: Resources("Y"),
                Reset=lambda: None,
            ),
        )
        action = SimpleNamespace(GetPlayer=lambda: contributor)
        paying_effect = Mock()
        paying_effect.context = SimpleNamespace(initiator=None)
        paying_effect.this = object()
        main_effect = SimpleNamespace(
            context=SimpleNamespace(initiator=resolver),
            targets=[],
            world=SimpleNamespace(DiscardResourcesArea=lambda: None),
        )
        cost_check = object()
        payment = TargetCost.Payment(
            Cost("1"),
            [],
            [{paying_effect: "Y"}],
            {paying_effect: cost_check},
        )

        with patch.object(Message, "WhenPlayerPayingResources") as paying_message, \
            patch.object(Message, "AfterCardsBeSpendAsResource") as spent_message:
            paid = PlayerAction.SpendResource(action, main_effect, [paying_effect], payment)

        self.assertEqual(paid.text_legacy, "Y")
        self.assertIs(main_effect.context.initiator, resolver)
        self.assertIs(paying_effect.context.initiator, contributor)
        paying_message.return_value.Send.assert_called_once()
        spent_message.return_value.Send.assert_called_once()

    def test_event_with_two_play_abilities_offers_one_selection(self):
        first_effect = object()
        second_effect = object()
        selected_effect = object()
        face = Mock()
        face.GetTurnPlayEffects.return_value = [first_effect, second_effect]
        face.card.can_state = SimpleNamespace(is_like_in_hand=None)
        player = Mock()
        player.GetIdentity.return_value = object()
        player.ChooseEffects.return_value = selected_effect
        action = SimpleNamespace(GetPlayer=lambda: player)

        with patch("game.card.face.attribute.has_cost.HasCost.IsType", return_value=True):
            played = PlayerAction.PlayCardsLikeInTurn(action, [face], Mock())

        self.assertEqual(played, [face])
        player.ChooseEffects.assert_called_once()
        chosen_effects = player.ChooseEffects.call_args.args[0]
        self.assertEqual(chosen_effects, [first_effect, second_effect])


if __name__ == "__main__":
    unittest.main()
