from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

# Preserve the application's normal import ordering.
from engine import Engine

from game.effect.effect_checker import EffectChecker
from game.effect.effect_target_cost import TargetCost
from game.element.cost import Cost
from game.element.resources import Resources
from game.card.face.base.card_player import ClassCard
from game.player.action.player_action import PlayerAction


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
        card = SimpleNamespace(area=source)
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
            context=SimpleNamespace(paid_this_resources=Resources("0")),
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


if __name__ == '__main__':
    unittest.main()
