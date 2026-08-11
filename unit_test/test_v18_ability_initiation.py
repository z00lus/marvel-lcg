from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

# Preserve the application's normal import ordering.
from engine import Engine

from game.effect.effect_checker import EffectChecker
from game.effect.effect import Effect
from game.effect.effect_context import EffectContext
from game.effect.effect_target_cost import TargetCost
from game.element.cost import Cost
from game.element.resources import Resources
from game.ability.cost_func import CostFunc
from game.card.card import Card
from game.card.states import CardIsStates
from game.card.face.base.card_player import ClassCard
from game.player.action.player_action import PlayerAction
from game.world.world_stat import WorldStat


class _PlayerActionHarness(PlayerAction):

    def __init__(self, player):
        self.player = player

    def GetPlayer(self):
        return self.player


class V18PlayInitiationOrderTests(unittest.TestCase):

    def MakePlay(self):
        source = SimpleNamespace(
            flags=SimpleNamespace(is_processing=False),
            GetIndex=lambda face: 3,
        )
        processing = SimpleNamespace(
            flags=SimpleNamespace(is_processing=True),
        )
        card = SimpleNamespace(
            area=source,
            can_state=SimpleNamespace(is_like_in_hand=None),
        )
        face = Mock()
        face.card = card
        face.IsLikeInHand.return_value = True
        face.IsInProcessingArea.side_effect = lambda: card.area is processing
        face.CastTo.return_value = face
        face.Play.return_value = True

        checker = Mock()
        checker.CheckPlayInitiation.return_value = True
        checker.CheckBeforeActive.return_value = True
        effect = SimpleNamespace(
            this=face,
            checker=checker,
            ability=SimpleNamespace(
                is_play=True,
                selectors=[],
                flags=SimpleNamespace(is_delay_ability=False),
            ),
            context=SimpleNamespace(
                paid_this_resources=Resources("0"),
                ResetFailedInitiation=Mock(),
            ),
            ClearPreparedSelfCosts=Mock(),
        )
        player = SimpleNamespace(
            stat=Mock(),
            world=SimpleNamespace(
                buff_manager=Mock(),
                render=Mock(),
            ),
            controller=SimpleNamespace(manager=Mock()),
        )
        action = _PlayerActionHarness(player)

        def place_on_table(faces, by_effect):
            card.area = processing
            return list(faces)

        def restore(faces, area, by_effect, *, index=-1):
            self.assertEqual(index, 3)
            card.area = area
            return list(faces)

        return action, player, effect, face, source, processing, place_on_table, restore

    def test_selected_card_is_on_table_before_normative_restriction_check(self):
        action, _, effect, face, _, processing, place, restore = self.MakePlay()

        def check_after_placement(message, player):
            self.assertIs(face.card.area, processing)
            return True

        effect.checker.CheckPlayInitiation.side_effect = check_after_placement

        with patch('game.operate.faces.Faces.MoveAllToProcessingArea', side_effect=place), \
             patch('game.operate.faces.Faces.MoveAllTo', side_effect=restore):
            self.assertTrue(action.ResolveEffect(effect, object()))

        effect.checker.CheckPlayInitiation.assert_called_once()
        effect.checker.CheckBeforeActive.assert_called_once()
        face.Play.assert_called_once()

    def test_from_hand_payment_eligibility_survives_table_declaration(self):
        action, _, effect, face, _, processing, place, restore = self.MakePlay()

        def check_after_placement(message, player):
            self.assertIs(face.card.area, processing)
            self.assertIs(face.card.can_state.is_like_in_hand, True)
            return True

        effect.checker.CheckPlayInitiation.side_effect = check_after_placement

        with patch('game.operate.faces.Faces.MoveAllToProcessingArea', side_effect=place), \
             patch('game.operate.faces.Faces.MoveAllTo', side_effect=restore):
            self.assertTrue(action.ResolveEffect(effect, object()))

        effect.checker.CheckPlayInitiation.assert_called_once()
        effect.checker.CheckBeforeActive.assert_called_once()
        face.Play.assert_called_once()

    def test_failed_restriction_returns_declared_card_to_its_source(self):
        action, _, effect, face, source, _, place, restore = self.MakePlay()
        effect.checker.CheckPlayInitiation.return_value = False

        with patch('game.operate.faces.Faces.MoveAllToProcessingArea', side_effect=place), \
             patch('game.operate.faces.Faces.MoveAllTo', side_effect=restore) as move_back, \
             patch('game.operate.faces.Faces.DiscardAll') as discard, \
             patch('game.test.Test.IsInTesting', return_value=False), \
             patch('game.player.action.player_action.Log.Assert'):
            self.assertFalse(action.ResolveEffect(effect, object()))

        self.assertIs(face.card.area, source)
        move_back.assert_called_once_with([face], source, effect, index=3)
        discard.assert_not_called()
        effect.checker.CheckBeforeActive.assert_not_called()
        face.Play.assert_not_called()

    def test_form_change_during_payment_does_not_recheck_passed_restriction(self):
        action, player, effect, face, _, _, place, restore = self.MakePlay()
        player.form = "hero"

        def pay_after_restriction(_player):
            player.form = "alter-ego"
            return True

        effect.checker.CheckBeforeActive.side_effect = pay_after_restriction

        with patch('game.operate.faces.Faces.MoveAllToProcessingArea', side_effect=place), \
             patch('game.operate.faces.Faces.MoveAllTo', side_effect=restore):
            self.assertTrue(action.ResolveEffect(effect, object()))

        self.assertEqual(player.form, "alter-ego")
        effect.checker.CheckPlayInitiation.assert_called_once()
        face.Play.assert_called_once()

    def test_failed_additional_cost_returns_card_and_records_no_play(self):
        action, player, effect, face, source, _, place, restore = self.MakePlay()
        face.Play.return_value = False

        with patch('game.operate.faces.Faces.MoveAllToProcessingArea', side_effect=place), \
             patch('game.operate.faces.Faces.MoveAllTo', side_effect=restore) as move_back, \
             patch('game.operate.faces.Faces.DiscardAll') as discard, \
             patch('game.test.Test.IsInTesting', return_value=False), \
             patch('game.player.action.player_action.Log.Assert'):
            self.assertFalse(action.ResolveEffect(effect, object()))

        self.assertIs(face.card.area, source)
        move_back.assert_called_once_with([face], source, effect, index=3)
        discard.assert_not_called()
        player.stat.RecordPlayedFace.assert_not_called()
        player.world.buff_manager.OnRecordPlayedFace.assert_not_called()

    def test_canceling_cost_choice_returns_declared_card_to_its_source(self):
        action, _, effect, face, source, _, place, restore = self.MakePlay()
        effect.checker.CheckBeforeActive.return_value = False

        with patch('game.operate.faces.Faces.MoveAllToProcessingArea', side_effect=place), \
             patch('game.operate.faces.Faces.MoveAllTo', side_effect=restore) as move_back, \
             patch('game.operate.faces.Faces.DiscardAll') as discard, \
             patch('game.test.Test.IsInTesting', return_value=False), \
             patch('game.player.action.player_action.Log.Assert'):
            self.assertFalse(action.ResolveEffect(effect, object()))

        self.assertIs(face.card.area, source)
        move_back.assert_called_once_with([face], source, effect, index=3)
        discard.assert_not_called()
        face.Play.assert_not_called()
        effect.ClearPreparedSelfCosts.assert_called_once()
        effect.context.ResetFailedInitiation.assert_called_once()


class V18FailedInitiationContextTests(unittest.TestCase):

    def MakeContext(self):
        owner = object()
        effect = SimpleNamespace(
            this=SimpleNamespace(GetControlByOrOwner=lambda: owner),
        )
        context = EffectContext(effect)
        return context, owner

    def test_failed_initiation_clears_targets_payment_and_cached_legality(self):
        context, owner = self.MakeContext()
        context.targets_internal = [object()]
        context.all_legal_targets = [object()]
        context.target_range = (1, 2)
        context.paid_this_res_effects = [object()]
        context.paid_this_resources = Resources("YR")
        context.paid_this_cost = Cost("2")
        context.this_effect_need_cost = Cost("2")
        context.chosen_cost_x = 2
        context.play_initiation_checked = True
        context.play_initiation_allowed = True
        context.self_costs_prepared = True
        context.allowed_removed_cards.add(object())

        context.ResetFailedInitiation()

        self.assertEqual(context.targets_internal, [])
        self.assertEqual(context.all_legal_targets, [])
        self.assertEqual(context.target_range, (0, 0))
        self.assertEqual(context.paid_this_res_effects, [])
        self.assertEqual(context.paid_this_resources.val, 0)
        self.assertEqual(context.paid_this_cost.val, 0)
        self.assertIsNone(context.this_effect_need_cost)
        self.assertIsNone(context.chosen_cost_x)
        self.assertFalse(context.play_initiation_checked)
        self.assertFalse(context.play_initiation_allowed)
        self.assertFalse(context.self_costs_prepared)
        self.assertEqual(context.allowed_removed_cards, set())
        self.assertIs(context.initiator, owner)

    def test_successful_operation_cleanup_clears_resolved_targets(self):
        context, _ = self.MakeContext()
        context.targets_internal = [object()]

        context.ResetAfterOperation()

        self.assertEqual(context.targets_internal, [])

    def test_normative_play_check_is_cached_for_one_initiation(self):
        context = SimpleNamespace(
            play_initiation_checked=False,
            play_initiation_allowed=False,
            ask_player=None,
        )
        effect = SimpleNamespace(
            context=context,
            this=SimpleNamespace(
                card=SimpleNamespace(
                    area=SimpleNamespace(
                        flags=SimpleNamespace(is_processing=True),
                    ),
                ),
            ),
        )
        checker = EffectChecker.__new__(EffectChecker)
        checker.effect = effect
        checker.ability = SimpleNamespace(is_play=True)
        checker.CheckCondition = Mock(return_value=True)
        player = object()
        message = object()

        self.assertTrue(checker.CheckPlayInitiation(message, player))
        self.assertTrue(checker.CheckPlayInitiation(message, player))

        checker.CheckCondition.assert_called_once_with(
            message,
            player,
            initiating_play=True,
        )

    def test_table_check_skips_only_the_preflight_hand_condition(self):
        player = Mock()
        processing = SimpleNamespace(
            flags=SimpleNamespace(
                is_processing=True,
                is_revealing=False,
            ),
        )
        face = Mock()
        face.card.area = processing
        face.GetOwner.return_value = player
        hand_condition = Mock(return_value=False)
        form_condition = Mock(return_value=True)
        ability = SimpleNamespace(
            conditions=[hand_condition, form_condition],
            play_location_condition=hand_condition,
            is_play=True,
            selectors=[],
            flags=SimpleNamespace(
                is_statistics=False,
                is_nonkeyword=False,
                is_setup=False,
                is_when_reveal=False,
                is_boost=False,
                is_delay_ability=False,
                is_forced_action=False,
            ),
            can_work_only_in_hand=False,
            NeedCost=lambda: False,
            is_label_defense=False,
        )
        context = SimpleNamespace(
            play_initiation_checked=False,
            play_initiation_allowed=False,
            ask_player=None,
        )
        effect = SimpleNamespace(
            this=face,
            ability=ability,
            context=context,
            world=SimpleNamespace(
                is_game_started=True,
                rule=SimpleNamespace(v17_actions_activations_costs=True),
            ),
            cost_func=SimpleNamespace(GetAll=lambda: []),
            is_forced=False,
            initiator=player,
        )
        checker = EffectChecker.__new__(EffectChecker)
        checker.effect = effect
        checker.ability = ability
        checker.failures = Mock()
        checker.CheckNotOutOfPlay = Mock(return_value=True)
        checker.UpdateLegalTargets = Mock(return_value=True)
        checker.HasCostTargets = Mock(return_value=True)
        message = SimpleNamespace(send_resolve_message=False)

        self.assertTrue(checker.CheckPlayInitiation(message, player))

        hand_condition.assert_not_called()
        form_condition.assert_called_once_with(effect, message)


class V18PlayPaymentRollbackTests(unittest.TestCase):

    def test_failed_additional_cost_does_not_discard_the_declared_card(self):
        player = object()
        face = SimpleNamespace(
            card=SimpleNamespace(
                area=SimpleNamespace(
                    flags=SimpleNamespace(is_processing=True),
                ),
            ),
        )
        has_cost = Mock()
        effect = SimpleNamespace(
            context=SimpleNamespace(paid_this_resources=Resources("0")),
            this=Mock(),
            GetInitiator=lambda: player,
            ProcessSelfCost=Mock(return_value=False),
        )
        effect.this.CastTo.return_value = has_cost

        with patch('game.operate.faces.Faces.DiscardAll') as discard:
            self.assertFalse(
                ClassCard.Play(
                    face,
                    player,
                    effect,
                    object(),
                    Resources("0"),
                    object(),
                    True,
                )
            )

        discard.assert_not_called()

    def MakeChecker(self, chosen_resources: str, cost: str, *, component_costs=()):
        payment_effect = object()
        payment = TargetCost.Payment(
            Cost(cost),
            list(component_costs),
            [{payment_effect: chosen_resources}],
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
            cost_func=SimpleNamespace(GetAll=lambda: []),
            PrepareSelfCosts=Mock(return_value=True),
            ValidatePreparedSelfCosts=Mock(return_value=True),
            ClearPreparedSelfCosts=Mock(),
            world=SimpleNamespace(
                rule=SimpleNamespace(v17_actions_activations_costs=True),
            ),
        )
        checker = EffectChecker.__new__(EffectChecker)
        checker.effect = effect
        checker.ability = SimpleNamespace(selectors=[])
        checker.cost_for_different_target = target_cost
        checker.failures = Mock()
        player = Mock()
        return checker, player

    def test_insufficient_selected_resources_are_not_spent(self):
        checker, player = self.MakeChecker("Y", "2")

        self.assertFalse(checker.CheckBeforeActive(player))

        player.SpendResource.assert_not_called()
        player.res_pool.Reset.assert_not_called()

    def test_canceling_simultaneous_allocation_does_not_spend_resources(self):
        checker, player = self.MakeChecker(
            "YY",
            "2",
            component_costs=[Cost("1"), Cost("1")],
        )
        player.AskChooseResourceAllocation.return_value = None

        self.assertFalse(checker.CheckBeforeActive(player))

        player.SpendResource.assert_not_called()
        player.res_pool.Reset.assert_not_called()

    def test_conflicting_prepared_costs_do_not_spend_resources(self):
        checker, player = self.MakeChecker("Y", "1")
        checker.effect.ValidatePreparedSelfCosts.return_value = False

        self.assertFalse(checker.CheckBeforeActive(player))

        checker.effect.ClearPreparedSelfCosts.assert_called_once()
        player.SpendResource.assert_not_called()
        player.res_pool.Reset.assert_not_called()


class V18AbilityInitiationChecklistTests(unittest.TestCase):

    def MakeConditionChecker(self, conditions, *, need_cost=True):
        player = Mock()
        face = Mock()
        face.card.area = SimpleNamespace(
            flags=SimpleNamespace(is_revealing=False),
        )
        ability = SimpleNamespace(
            conditions=list(conditions),
            play_location_condition=None,
            is_play=False,
            selectors=[object()],
            flags=SimpleNamespace(
                is_statistics=False,
                is_nonkeyword=False,
                is_setup=False,
                is_when_reveal=False,
                is_boost=False,
                is_forced_action=False,
            ),
            NeedCost=lambda: need_cost,
            is_label_defense=False,
        )
        effect = SimpleNamespace(
            this=face,
            ability=ability,
            context=SimpleNamespace(),
            world=SimpleNamespace(is_game_started=True),
            cost_func=SimpleNamespace(GetAll=lambda: []),
            is_forced=False,
            initiator=player,
        )
        checker = EffectChecker.__new__(EffectChecker)
        checker.effect = effect
        checker.ability = ability
        checker.failures = Mock()
        checker.CheckNotOutOfPlay = Mock(return_value=True)
        checker.UpdateLegalTargets = Mock(return_value=True)
        checker.HasCostTargets = Mock(return_value=True)
        checker.UpdatePayResources = Mock(return_value=True)
        checker.RequiresPayableResourceCost = Mock(return_value=False)
        message = SimpleNamespace(send_resolve_message=False)
        return checker, player, message

    def test_unavailable_ability_stops_before_targets_or_costs(self):
        calls = []

        def unavailable(effect, message):
            calls.append((effect, message))
            return False

        checker, player, message = self.MakeConditionChecker([unavailable])

        self.assertFalse(checker.CheckCondition(message, player))

        self.assertEqual(calls, [(checker.effect, message)])
        checker.UpdateLegalTargets.assert_not_called()
        checker.HasCostTargets.assert_not_called()
        checker.UpdatePayResources.assert_not_called()

    def test_legal_targets_are_checked_before_cost_targets_and_resources(self):
        order = []
        checker, player, message = self.MakeConditionChecker([])
        checker.UpdateLegalTargets.side_effect = lambda *_: order.append('targets') or True
        checker.HasCostTargets.side_effect = lambda: order.append('cost targets') or True
        checker.UpdatePayResources.side_effect = lambda *_: order.append('resources') or True

        self.assertTrue(checker.CheckCondition(message, player))

        self.assertEqual(order, ['targets', 'cost targets', 'resources'])

    def test_target_confirmation_precedes_cost_preparation_and_resource_spend(self):
        order = []
        target = object()
        resource_effect = object()
        selector = Mock()
        selector.AfterSelectTargets.side_effect = \
            lambda *_: order.append('target confirmed') or True
        payment = TargetCost.Payment(
            Cost('1'),
            [],
            [{resource_effect: 'Y'}],
            {resource_effect: object()},
        )
        target_cost = TargetCost()
        target_cost.SetNoneTargetOnly()
        target_cost.target_cost[None] = payment
        context = SimpleNamespace(
            ignore_resource_cost=False,
            paid_this_res_effects=[resource_effect],
            paid_this_cost=Cost('0'),
            paid_this_resources=Resources('0'),
            this_effect_need_cost=None,
            targets_internal=[target],
            target_range=(1, 1),
        )
        effect = SimpleNamespace(
            targets=[target],
            context=context,
            cost_func=SimpleNamespace(GetAll=lambda: []),
            PrepareSelfCosts=Mock(
                side_effect=lambda: order.append('costs prepared') or True,
            ),
            ValidatePreparedSelfCosts=Mock(
                side_effect=lambda: order.append('costs validated') or True,
            ),
            ClearPreparedSelfCosts=Mock(),
        )
        checker = EffectChecker.__new__(EffectChecker)
        checker.effect = effect
        checker.ability = SimpleNamespace(selectors=[selector])
        checker.cost_for_different_target = target_cost
        checker.failures = Mock()
        player = Mock()
        player.SpendResource.side_effect = \
            lambda *_: order.append('resources spent') or Resources('Y')

        self.assertTrue(checker.CheckBeforeActive(player))

        self.assertEqual(
            order,
            [
                'target confirmed',
                'costs prepared',
                'costs validated',
                'resources spent',
            ],
        )

    def test_canceling_a_later_cost_does_not_commit_an_earlier_cost(self):
        mutation = []
        target = Mock()
        target.IsInDeck.return_value = True

        def make_cost(*, selectable):
            selector = Mock()
            selector.GetAllLegalTargets.return_value = [target]
            selector.GetTargetRange.return_value = (1, 1)
            selector.AfterSelectTargets.return_value = selectable
            selector.selector_rule.random = False
            return CostFunc.Base(
                selector,
                lambda *_: mutation.append('committed') or True,
            )

        first = make_cost(selectable=True)
        canceled = make_cost(selectable=False)
        effect = object.__new__(Effect)
        effect.context = SimpleNamespace(
            self_costs_prepared=False,
            initiator=Mock(),
        )
        effect.cost_func = SimpleNamespace(GetAll=lambda: [first, canceled])
        effect.ability = SimpleNamespace(
            flags=SimpleNamespace(is_check_pay=False),
        )
        effect.world = SimpleNamespace(render=Mock())

        self.assertFalse(Effect.PrepareSelfCosts(effect))

        self.assertEqual(mutation, [])
        self.assertEqual(first.cost_legal_targets, [])
        self.assertEqual(canceled.cost_legal_targets, [])

    def test_failed_cost_preparation_does_not_spend_resources(self):
        resource_effect = object()
        payment = TargetCost.Payment(
            Cost('1'),
            [],
            [{resource_effect: 'Y'}],
            {resource_effect: object()},
        )
        target_cost = TargetCost()
        target_cost.SetNoneTargetOnly()
        target_cost.target_cost[None] = payment
        context = SimpleNamespace(
            ignore_resource_cost=False,
            paid_this_res_effects=[resource_effect],
            paid_this_cost=Cost('0'),
            paid_this_resources=Resources('0'),
            this_effect_need_cost=None,
            targets_internal=[],
        )
        effect = SimpleNamespace(
            targets=[],
            context=context,
            cost_func=SimpleNamespace(GetAll=lambda: []),
            PrepareSelfCosts=Mock(return_value=False),
            ValidatePreparedSelfCosts=Mock(return_value=True),
            ClearPreparedSelfCosts=Mock(),
        )
        checker = EffectChecker.__new__(EffectChecker)
        checker.effect = effect
        checker.ability = SimpleNamespace(selectors=[])
        checker.cost_for_different_target = target_cost
        checker.failures = Mock()
        player = Mock()

        self.assertFalse(checker.CheckBeforeActive(player))

        player.SpendResource.assert_not_called()
        player.res_pool.Reset.assert_not_called()

    def test_exhaust_cost_cannot_exhaust_the_same_card_twice(self):
        card = object.__new__(Card)
        card.state = CardIsStates()
        card.face = object()
        effect = object()
        after_message = Mock()

        with patch(
            'game.message.Message.AfterCardExhausted',
            return_value=after_message,
        ) as after:
            self.assertTrue(Card.Exhaust(card, effect))
            self.assertFalse(Card.Exhaust(card, effect))

        self.assertFalse(card.state.is_ready)
        after.assert_called_once()
        after_message.Send.assert_called_once()

    def test_once_per_phase_and_round_limits_reset_at_their_boundaries(self):
        stat = WorldStat()
        ability = object()
        effect = SimpleNamespace(ability=ability)
        player = object()

        stat.RecordEffect(effect)
        stat.RecordEffectWithPlayer(effect, player)
        self.assertFalse(stat.IsOncePerGame(ability))
        self.assertFalse(stat.IsOncePerPhase(ability))
        self.assertFalse(stat.IsOncePerRound(ability))
        self.assertFalse(stat.IsOncePerPhasePerPlayer(ability, player))
        self.assertFalse(stat.IsOncePerRoundPerPlayer(ability, player))

        stat.OnPhaseEnd()
        self.assertFalse(stat.IsOncePerGame(ability))
        self.assertTrue(stat.IsOncePerPhase(ability))
        self.assertTrue(stat.IsOncePerPhasePerPlayer(ability, player))
        self.assertFalse(stat.IsOncePerRound(ability))
        self.assertFalse(stat.IsOncePerRoundPerPlayer(ability, player))

        stat.OnRoundEnd()
        self.assertFalse(stat.IsOncePerGame(ability))
        self.assertTrue(stat.IsOncePerRound(ability))
        self.assertTrue(stat.IsOncePerRoundPerPlayer(ability, player))

    def test_once_per_game_limit_is_reconstructed_by_replaying_the_activation(self):
        ability = object()

        def reconstruct_stat():
            stat = WorldStat()
            stat.RecordEffect(SimpleNamespace(ability=ability))
            return stat

        original = reconstruct_stat()
        continued = reconstruct_stat()

        self.assertFalse(original.IsOncePerGame(ability))
        self.assertFalse(continued.IsOncePerGame(ability))
        for stat in (original, continued):
            stat.OnPhaseEnd()
            stat.OnRoundEnd()
            stat.OnTurnEnd()
            self.assertFalse(stat.IsOncePerGame(ability))

if __name__ == '__main__':
    unittest.main()
