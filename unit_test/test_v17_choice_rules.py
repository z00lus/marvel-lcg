import importlib
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

# Match the application's normal import order without initializing the server.
from engine import Engine

from game.card.face import EncounterCard, PlayerCard
from game.card.card_finder import CardFinder
from game.effect.effect import Effect
from game.effect.effect_checker import EffectChecker
from game.effect.effect_target_cost import TargetCost
from game.element.cost import Cost
from game.element.resources import Resources
from game.event.manager import EventManager
from game.message import Message
from game.player.action.player_action import PlayerAction
from game.selector import Select


class PartialChoiceTargetTests(unittest.TestCase):

    def test_old_rules_require_the_full_number_of_targets(self):
        target = Mock()
        selector = Select.From(faces=[target], range=(2, 2))

        self.assertIsNone(selector.GetTargetRange(Mock(), [target]))

    def test_v17_choice_can_partially_resolve_with_one_target(self):
        target = Mock()
        selector = Select.From(faces=[target], range=(2, 2))

        self.assertEqual(
            selector.GetTargetRange(Mock(), [target], allow_partial=True),
            (1, 1),
        )

    def test_v17_choice_still_rejects_an_option_without_targets(self):
        selector = Select.From(faces=[], range=(2, 2))

        self.assertIsNone(
            selector.GetTargetRange(Mock(), [], allow_partial=True),
        )

    def test_partial_choice_does_not_leave_full_trait_requirement_in_ui(self):
        selector = Select.From(
            finder=CardFinder(traits=["ATTACK", "DEFENSE"]),
            range=(2, 2),
            select_rule="MustIncludeTraits",
        )
        effect = SimpleNamespace(
            object_id=1,
            ability=SimpleNamespace(name="Choice", selectors=[selector]),
            this=SimpleNamespace(card=SimpleNamespace(object_id=2)),
            context=SimpleNamespace(
                allow_partial_resolution=True,
                all_legal_targets=[],
                target_range=(1, 1),
                ignore_resource_cost=False,
            ),
            checker=SimpleNamespace(cost_for_different_target=TargetCost()),
            failures=SimpleNamespace(
                GetText=lambda player_id: "",
                IsNoProcess=lambda player_id: False,
            ),
            GetDisplayName=lambda remove_space=True: "Choice",
        )

        descriptor = Effect.Render(effect, None, 0)

        self.assertEqual(descriptor.target_must_include_traits, [])


class ChoicePaymentTests(unittest.TestCase):

    def test_combined_resources_can_pay_player_choice_cost(self):
        target_cost = TargetCost()
        target_cost.AddTarget(None, Cost("RR"))
        target_cost.AddPayment(None, Mock(), Resources("R"), Mock())
        target_cost.AddPayment(None, Mock(), Resources("R"), Mock())

        self.assertTrue(target_cost.HasPayableTarget())

    def test_wrong_resource_combination_cannot_pay_player_choice_cost(self):
        target_cost = TargetCost()
        target_cost.AddTarget(None, Cost("RR"))
        target_cost.AddPayment(None, Mock(), Resources("R"), Mock())
        target_cost.AddPayment(None, Mock(), Resources("B"), Mock())

        self.assertFalse(target_cost.HasPayableTarget())

    def test_zero_cost_is_payable_without_resource_effects(self):
        target_cost = TargetCost()
        target_cost.AddTarget(None, Cost("0"))

        self.assertTrue(target_cost.HasPayableTarget())


class ChoiceSourceTests(unittest.TestCase):

    def MakeChecker(self, source):
        source.consider_as = SimpleNamespace(card_types={})
        message = object.__new__(Message.WhenPlayerChooseAbility)
        message.by_effect = SimpleNamespace(this=source)

        effect = Mock()
        effect.bind_message = message
        effect.GetBindMessage.return_value = message

        checker = object.__new__(EffectChecker)
        checker.effect = effect
        return checker

    def test_player_card_choice_is_identified_for_cost_validation(self):
        checker = self.MakeChecker(object.__new__(PlayerCard))

        self.assertTrue(checker.IsChoiceOption())
        self.assertTrue(checker.IsPlayerCardChoiceOption())

    def test_encounter_choice_does_not_use_player_cost_validation(self):
        checker = self.MakeChecker(object.__new__(EncounterCard))

        self.assertTrue(checker.IsChoiceOption())
        self.assertFalse(checker.IsPlayerCardChoiceOption())

    def MakeConditionChecker(self, source, *, need_cost):
        source.consider_as = SimpleNamespace(card_types={})
        message = object.__new__(Message.WhenPlayerChooseAbility)
        message.by_effect = SimpleNamespace(this=source)
        message.send_resolve_message = False
        message.for_second_target = False

        ability = Mock()
        ability.conditions = []
        ability.selectors = []
        ability.is_play = False
        ability.is_label_defense = False
        ability.NeedCost.return_value = need_cost
        ability.flags.is_statistics = False

        asked_player = Mock()
        this = Mock()
        this.card.area.flags.is_revealing = False

        effect = Mock()
        effect.ability = ability
        effect.this = this
        effect.bind_message = message
        effect.world.is_game_started = True
        effect.cost_func.GetAll.return_value = []
        effect.is_forced = False
        effect.initiator = asked_player
        effect.context = SimpleNamespace(
            ignore_resource_cost=False,
            allow_partial_resolution=False,
        )
        effect.GetBindMessage.return_value = message

        checker = EffectChecker(effect)
        checker.CheckNotOutOfPlay = Mock(return_value=True)
        checker.HasCostTargets = Mock(return_value=True)
        return checker, message, asked_player

    def test_unpayable_player_card_choice_is_unavailable(self):
        checker, message, asked_player = self.MakeConditionChecker(
            object.__new__(PlayerCard),
            need_cost=True,
        )
        checker.UpdateLegalTargets = Mock(return_value=True)
        checker.UpdatePayResources = Mock()

        self.assertFalse(checker.CheckCondition(message, asked_player))

    def test_encounter_choice_does_not_require_a_resource_payment(self):
        checker, message, asked_player = self.MakeConditionChecker(
            object.__new__(EncounterCard),
            need_cost=True,
        )
        checker.UpdateLegalTargets = Mock(return_value=True)
        checker.UpdatePayResources = Mock()

        self.assertTrue(checker.CheckCondition(message, asked_player))

    def test_search_choice_without_a_guaranteed_match_remains_available(self):
        checker, message, asked_player = self.MakeConditionChecker(
            object.__new__(PlayerCard),
            need_cost=False,
        )

        self.assertTrue(checker.CheckCondition(message, asked_player))
        self.assertTrue(checker.effect.context.allow_partial_resolution)


class OtherwiseChoiceTests(unittest.TestCase):

    @staticmethod
    def Effect(*, otherwise=False):
        return SimpleNamespace(
            context=SimpleNamespace(
                only_work_when_no_other_options=otherwise,
            ),
        )

    def test_otherwise_is_available_when_its_preceding_option_is_not(self):
        other_option = self.Effect()
        preceding = self.Effect()
        otherwise = self.Effect(otherwise=True)

        filtered = EventManager.FilterOtherwiseChoices(
            [other_option, preceding, otherwise],
            [other_option, otherwise],
        )

        self.assertEqual(filtered, [other_option, otherwise])

    def test_otherwise_is_hidden_when_its_preceding_option_is_available(self):
        other_option = self.Effect()
        preceding = self.Effect()
        otherwise = self.Effect(otherwise=True)

        filtered = EventManager.FilterOtherwiseChoices(
            [other_option, preceding, otherwise],
            [other_option, preceding, otherwise],
        )

        self.assertEqual(filtered, [other_option, preceding])


class SequentialForEachChoiceTests(unittest.TestCase):

    def test_each_instance_is_built_after_the_previous_one_resolves(self):
        player = Mock()
        state = {"guard_in_play": True}
        offered_targets = []

        def build_abilities(index):
            target = "guard" if state["guard_in_play"] else "villain"
            offered_targets.append(target)
            return [target]

        def resolve(by_effect, target, *, forced, step):
            if target == "guard":
                state["guard_in_play"] = False
            return SimpleNamespace(target=target, step=step)

        player.ChooseAbilitiesHelper.side_effect = resolve
        by_effect = SimpleNamespace(
            world=SimpleNamespace(
                is_game_over=False,
                rule=SimpleNamespace(v17_choice=True),
            ),
        )

        effects = PlayerAction.ChooseForEach(
            player,
            by_effect,
            2,
            build_abilities,
        )

        self.assertEqual(offered_targets, ["guard", "villain"])
        self.assertEqual([effect.step for effect in effects], [(1, 2), (2, 2)])

    def test_strength_in_diversity_uses_sequential_for_each_choices(self):
        module = importlib.import_module("cards.pack.falcon.53019")
        ability = module.GetAbilities()[0]
        event = Mock()
        player = Mock()
        effect = Mock()
        effect.this.CastTo.return_value = event
        effect.GetInitiator.return_value = player

        with patch.object(module.Worlds, "GetOnFieldFriendlyCharacters", return_value=[Mock()]), \
             patch.object(module.Faces, "CountTraitNum", return_value=2):
            ability.operation(effect, Mock())

        args = player.ChooseForEach.call_args.args
        self.assertEqual(args[:2], (effect, 2))
        self.assertEqual(len(args[2](0)), 2)


if __name__ == '__main__':
    unittest.main()
