from types import SimpleNamespace
import importlib
import unittest
from unittest.mock import Mock, patch

# Preserve the application's normal import ordering.
from engine import Engine

from game.ability.condition import Condition
from game.ability.cost_func import CostFunc
from game.card.face.attribute.can_place_counter import CanPlaceCounter
from game.card.face.attribute.can_place_token import CanPlaceToken
from game.effect.effect import Effect
from game.effect.effect_invoke import EffectInvoker
from game.selector.selector import Selector
from game.world.world_stat import WorldStat


class _Filter:

    def __init__(self):
        self.parameters = {}

    def AddParameter(self, **values):
        self.parameters.update(values)


class _PreparedSelector(Selector):

    def __init__(self, targets_fn):
        self.targets_fn = targets_fn
        self.selector_filter = _Filter()
        self.selector_end = SimpleNamespace(not_move=False)
        self.selector_rule = SimpleNamespace(random=False)

    def GetAllLegalTargets(self, effect, referential_effect=None, *, just_check=False):
        targets = list(self.targets_fn())
        check = self.selector_filter.parameters.get("check_effect_fn")
        if check:
            targets = [target for target in targets if check(effect, target)]
        return targets

    def GetTargetRange(self, effect, targets, *, allow_partial=False):
        if not targets:
            return None
        return (1, 1)

    def GetRandomTarget(self, targets, effect):
        return targets

    def AfterSelectTargets(self, effect, targets, target_range):
        return True

    def HasLegalTargets(self, effect):
        return bool(self.GetAllLegalTargets(effect, just_check=True))


class _ExhaustableFace:

    def __init__(self):
        self.ready = True

    def IsInDeck(self):
        return False

    def ExhaustInternal(self, effect, *, ui_group=False):
        if not self.ready:
            return False
        self.ready = False
        return True


def MakeEffect(*costs):
    effect = object.__new__(Effect)
    effect.context = SimpleNamespace(
        self_costs_prepared=False,
        initiator=object(),
    )
    effect.cost_func = SimpleNamespace(GetAll=lambda: list(costs))
    effect.ability = SimpleNamespace(
        flags=SimpleNamespace(is_check_pay=False),
    )
    return effect


class NonResourceCostContractTests(unittest.TestCase):

    def test_duplicate_exhaust_costs_fail_before_exhausting_the_card(self):
        face = _ExhaustableFace()
        first = CostFunc.Exhaust(_PreparedSelector(lambda: [face]))
        second = CostFunc.Exhaust(_PreparedSelector(lambda: [face]))
        effect = MakeEffect(first, second)

        with patch("game.message.Message.AfterCardsExhaust_Text"):
            self.assertFalse(effect.ProcessSelfCost())

        self.assertTrue(face.ready)

    def test_stale_later_cost_prevents_every_cost_commit(self):
        mutation = []
        first_target = Mock()
        first_target.IsInDeck.return_value = False
        first = CostFunc.Custom(
            _PreparedSelector(lambda: [first_target]),
            lambda targets, effect: mutation.append("committed") or True,
        )
        later_target = _ExhaustableFace()
        later = CostFunc.Exhaust(
            _PreparedSelector(
                lambda: [later_target] if later_target.ready else [],
            ),
        )
        effect = MakeEffect(first, later)

        self.assertTrue(effect.PrepareSelfCosts())
        later_target.ready = False
        self.assertFalse(effect.ProcessSelfCost())

        self.assertEqual(mutation, [])

    def test_custom_cost_precommit_validation_runs_before_mutation(self):
        face = Mock()
        face.IsInDeck.return_value = False
        selector = _PreparedSelector(lambda: [face])
        mutate = Mock(return_value=True)
        cost = CostFunc.Custom(
            selector,
            mutate,
            validate_fn=lambda targets, effect: False,
        )
        effect = MakeEffect(cost)

        self.assertFalse(effect.ProcessSelfCost())

        mutate.assert_not_called()

    def test_exhaust_cost_cannot_be_paid_twice_until_the_card_is_readied(self):
        face = _ExhaustableFace()
        selector = _PreparedSelector(lambda: [face] if face.ready else [])
        cost = CostFunc.Exhaust(selector)
        effect = MakeEffect(cost)

        with patch("game.message.Message.AfterCardsExhaust_Text"):
            self.assertTrue(effect.ProcessSelfCost())
            self.assertFalse(face.ready)
            self.assertFalse(effect.ProcessSelfCost())

            face.ready = True
            self.assertTrue(effect.ProcessSelfCost())
            self.assertFalse(face.ready)

    def test_discard_cost_delegates_destination_to_the_cards_owner(self):
        face = Mock()
        face.IsInDeck.return_value = False
        selector = _PreparedSelector(lambda: [face])
        cost = CostFunc.Discard(selector)
        effect = MakeEffect(cost)

        with patch(
            "game.operate.faces.Faces.DiscardAll",
            return_value=[face],
        ) as discard:
            self.assertTrue(effect.ProcessSelfCost())

        discard.assert_called_once_with([face], effect)

    def test_prevented_damage_cannot_partially_pay_a_damage_cost(self):
        unit = Mock()
        unit.health = 3
        unit.IsTough.return_value = False
        unit.TakeDamage.return_value = SimpleNamespace(took_damage=1)
        unit.IsDefeated.return_value = False
        face = Mock()
        face.IsInDeck.return_value = False
        face.health = 3
        face.IsTough.return_value = False
        face.CastTo.return_value = unit
        selector = _PreparedSelector(lambda: [face])
        cost = CostFunc.TakeDamage(2, selector)
        effect = MakeEffect(cost)
        effect.this = Mock()

        with patch(
            "game.ability.condition.card_type.ConditionCardType.TargetCanTakeDamage",
            return_value=True,
        ):
            self.assertFalse(effect.ProcessSelfCost())

        unit.TakeDamage.assert_called_once_with(effect.this, 2, effect)

    def test_tough_rejects_a_damage_cost_during_preparation(self):
        unit = Mock()
        unit.health = 5
        unit.IsTough.return_value = True
        face = Mock()
        face.health = 5
        face.IsInDeck.return_value = False
        face.CastTo.return_value = unit
        selector = _PreparedSelector(lambda: [face])
        cost = CostFunc.TakeDamage(2, selector)
        effect = MakeEffect(cost)

        with patch(
            "game.ability.condition.card_type.ConditionCardType.TargetCanTakeDamage",
            return_value=True,
        ):
            self.assertFalse(effect.ProcessSelfCost())

        unit.TakeDamage.assert_not_called()

    def test_lethal_damage_rejects_a_damage_cost_during_preparation(self):
        unit = Mock()
        unit.health = 2
        unit.IsTough.return_value = False
        face = Mock()
        face.health = 2
        face.IsInDeck.return_value = False
        face.CastTo.return_value = unit
        selector = _PreparedSelector(lambda: [face])
        cost = CostFunc.TakeDamage(2, selector)
        effect = MakeEffect(cost)

        with patch(
            "game.ability.condition.card_type.ConditionCardType.TargetCanTakeDamage",
            return_value=True,
        ):
            self.assertFalse(effect.ProcessSelfCost())

        unit.TakeDamage.assert_not_called()

    def test_combined_damage_cost_cannot_become_lethal(self):
        unit = Mock()
        unit.health = 3
        unit.IsTough.return_value = False
        face = Mock()
        face.health = 3
        face.IsInDeck.return_value = False
        face.CastTo.return_value = unit
        first = CostFunc.TakeDamage(2, _PreparedSelector(lambda: [face]))
        second = CostFunc.TakeDamage(2, _PreparedSelector(lambda: [face]))
        effect = MakeEffect(first, second)
        effect.this = Mock()

        with patch(
            "game.ability.condition.card_type.ConditionCardType.TargetCanTakeDamage",
            return_value=True,
        ):
            self.assertFalse(effect.ProcessSelfCost())

        unit.TakeDamage.assert_not_called()

    def test_insufficient_tokens_fail_during_preparation_without_removal(self):
        face = object.__new__(CanPlaceToken)
        face.card = SimpleNamespace(components=SimpleNamespace(token=Mock()))
        face.components.token.GetTokens.return_value = 1
        selector = _PreparedSelector(lambda: [face])
        cost = CostFunc.RemoveTokens(selector, 2, "charge")
        effect = MakeEffect(cost)

        with patch.object(
            CanPlaceToken,
            "RemoveTokensInternal",
        ) as remove:
            self.assertFalse(effect.ProcessSelfCost())

        remove.assert_not_called()

    def test_combined_token_cost_is_validated_before_any_removal(self):
        face = object.__new__(CanPlaceToken)
        face.card = SimpleNamespace(
            components=SimpleNamespace(token=Mock()),
            IsInDeck=Mock(return_value=False),
        )
        face.components.token.GetTokens.return_value = 3
        first = CostFunc.RemoveTokens(_PreparedSelector(lambda: [face]), 2, "charge")
        second = CostFunc.RemoveTokens(_PreparedSelector(lambda: [face]), 2, "charge")
        effect = MakeEffect(first, second)

        with patch.object(CanPlaceToken, "RemoveTokensInternal") as remove:
            self.assertFalse(effect.ProcessSelfCost())

        remove.assert_not_called()

    def test_combined_counter_cost_is_validated_before_any_removal(self):
        face = object.__new__(CanPlaceCounter)
        face.card = SimpleNamespace(
            components=SimpleNamespace(counter=Mock()),
            IsInDeck=Mock(return_value=False),
        )
        face.components.counter.GetCounters.return_value = 3
        first = CostFunc.Counter(_PreparedSelector(lambda: [face]), 2, "charge")
        second = CostFunc.Counter(_PreparedSelector(lambda: [face]), 2, "charge")
        effect = MakeEffect(first, second)

        with patch.object(CanPlaceCounter, "RemoveCountersInternal") as remove:
            self.assertFalse(effect.ProcessSelfCost())

        remove.assert_not_called()

    def test_navigation_column_cancellation_happens_before_exhaust(self):
        navigation_column = importlib.import_module(
            "cards.pack.gmw.the_market.16172",
        )
        costs = navigation_column.GetAbilities()[0].cost_funcs

        self.assertIsInstance(costs[0], CostFunc.Custom)
        self.assertIsInstance(costs[1], CostFunc.Exhaust)

        player = Mock()
        player.IsControl.return_value = False
        player.DiscardHandCards.return_value = []
        effect = Mock()
        effect.GetInitiator.return_value = player

        self.assertFalse(costs[0].call_fn([], effect, player))
        player.DiscardHandCards.assert_called_once_with((1, 1), effect)

    def test_teleport_drop_uses_the_attached_bamf_as_a_standard_discard_cost(self):
        teleport_drop = importlib.import_module(
            "cards.pack.ncrawler.nightcrawler.48008",
        )
        ability = teleport_drop.GetAbilities()[0]
        cost = ability.cost_funcs[0]
        bamf = Mock()
        target = Mock()
        target.GetInventoryDeck.return_value.FindCard.return_value = bamf
        effect = SimpleNamespace(targets=[target])

        self.assertIsInstance(cost, CostFunc.Discard)
        self.assertEqual(
            cost.selector.selector_target.get_targets_fn(effect),
            [bamf],
        )

    def test_energy_transfer_revalidates_touched_before_card_payment(self):
        energy_transfer = importlib.import_module(
            "cards.pack.rogue.rogue.38007",
        )
        cost = energy_transfer.GetAbilities()[0].cost_funcs[0]
        target = Mock()
        target.card.IsOnField.return_value = True
        effect = Mock()
        cost.cost_legal_targets = [target]

        with (
            patch.object(cost.selector, "GetAllLegalTargets", return_value=[target]),
            patch.object(energy_transfer, "FindTouched", return_value=None),
        ):
            self.assertFalse(cost.ValidatePreparedCost(effect))

        with (
            patch.object(cost.selector, "GetAllLegalTargets", return_value=[target]),
            patch.object(energy_transfer, "FindTouched", return_value=Mock()),
        ):
            self.assertTrue(cost.ValidatePreparedCost(effect))

    def test_failed_cost_does_not_consume_an_ability_limit(self):
        ability = SimpleNamespace()
        ability.flags = SimpleNamespace()
        world = SimpleNamespace(stat=WorldStat())
        effect = SimpleNamespace(
            ability=ability,
            initiator=object(),
            world=world,
            this=SimpleNamespace(GetControlBy=lambda: None),
            ProcessSelfCost=Mock(return_value=False),
        )

        resolved = EffectInvoker.ResolveSelfInternal(
            effect,
            SimpleNamespace(send_resolve_message=True),
            None,
            SimpleNamespace(),
        )

        self.assertFalse(resolved)
        self.assertTrue(world.stat.IsOncePerGame(ability))
        self.assertTrue(world.stat.IsOncePerRound(ability))
        self.assertTrue(world.stat.IsOncePerPhase(ability))

    def test_once_per_game_condition_survives_phase_and_round_boundaries(self):
        ability = object()
        effect = SimpleNamespace(
            ability=ability,
            world=SimpleNamespace(stat=WorldStat()),
        )
        message = object()

        self.assertTrue(Condition.LimitOncePerGame(effect, message))
        effect.world.stat.RecordEffect(SimpleNamespace(ability=ability))
        self.assertFalse(Condition.LimitOncePerGame(effect, message))

        effect.world.stat.OnPhaseEnd()
        effect.world.stat.OnRoundEnd()
        self.assertFalse(Condition.LimitOncePerGame(effect, message))


if __name__ == "__main__":
    unittest.main()
