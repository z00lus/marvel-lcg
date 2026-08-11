from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

# Preserve the application's normal import ordering.
from engine import Engine

from game.ability import Ability, AbilityType
from game.ability.condition import Condition
from game.card.face.base import Villain
from game.card.face.card_type import Obligation
from game.effect.effect_checker import EffectChecker
from game.effect.effect_failure import EffectFailure


class ActionAvailabilityMatrixTests(unittest.TestCase):

    def MakeChecker(
        self,
        ability_type=AbilityType.Action,
        *,
        conditions=None,
        need_cost=False,
    ):
        player = Mock(name="active_player")
        player.IsHero.return_value = False
        player.IsAlterEgo.return_value = False

        area = SimpleNamespace(
            flags=SimpleNamespace(
                is_processing=False,
                is_revealing=False,
            ),
        )
        face = Mock(name="source")
        face.card.area = area

        if conditions is None:
            conditions = Ability.GetAbilityTypeCondition(ability_type)
        ability = SimpleNamespace(
            conditions=list(conditions),
            play_location_condition=None,
            is_play=False,
            selectors=[],
            flags=ability_type.flags,
            can_work_only_in_hand=False,
            can_work_also_in_hand=False,
            is_ignore_out_of_play=False,
            NeedCost=lambda: need_cost,
            is_label_defense=False,
        )
        effect = SimpleNamespace(
            this=face,
            ability=ability,
            context=SimpleNamespace(ignore_resource_cost=False),
            world=SimpleNamespace(
                is_game_started=True,
                stat=Mock(),
            ),
            cost_func=SimpleNamespace(GetAll=lambda: []),
            is_forced=ability_type.flags.is_forced,
            initiator=player,
            GetInitiator=lambda: player,
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
        checker.cost_for_different_target = Mock()
        checker.cost_for_different_target.HasPayableTarget.return_value = True
        message = SimpleNamespace(send_resolve_message=False)
        return checker, player, message

    def test_ability_type_and_form_matrix(self):
        rows = (
            ("action", AbilityType.Action, "hero", True),
            ("action alter-ego", AbilityType.Action, "alter-ego", True),
            ("hero action in hero form", AbilityType.HeroAction, "hero", True),
            ("hero action in alter-ego form", AbilityType.HeroAction, "alter-ego", False),
            ("alter-ego action in alter-ego form", AbilityType.AlterEgoAction, "alter-ego", True),
            ("alter-ego action in hero form", AbilityType.AlterEgoAction, "hero", False),
            ("resource", AbilityType.Resource, "hero", True),
            ("interrupt", AbilityType.Interrupt, "hero", True),
            ("response", AbilityType.Response, "hero", True),
            ("forced interrupt", AbilityType.ForcedInterrupt, "hero", True),
            ("forced response", AbilityType.ForcedResponse, "hero", True),
        )

        for name, ability_type, form, expected in rows:
            with self.subTest(name=name):
                checker, player, message = self.MakeChecker(ability_type)
                player.IsHero.return_value = form == "hero"
                player.IsAlterEgo.return_value = form == "alter-ego"

                self.assertEqual(
                    checker.CheckCondition(message, player),
                    expected,
                )

                if expected:
                    checker.failures.Set.assert_called_with(
                        player,
                        EffectFailure.OK,
                    )
                else:
                    checker.UpdateLegalTargets.assert_not_called()
                    checker.HasCostTargets.assert_not_called()
                    checker.UpdatePayResources.assert_not_called()
                    checker.failures.SetText.assert_called_once()

    def test_availability_state_matrix(self):
        def wrong_timing(effect, message):
            return False

        rows = (
            ("legal", {}, True, EffectFailure.OK),
            (
                "wrong timing",
                {"conditions": [wrong_timing]},
                False,
                None,
            ),
            (
                "no mandatory target",
                {"legal_targets": False},
                False,
                EffectFailure.UpdateLegalTargets,
            ),
            (
                "exhausted cost source",
                {"cost_targets": False},
                False,
                EffectFailure.NoCostTarget,
            ),
            (
                "insufficient resources",
                {"need_cost": True, "payable": False},
                False,
                EffectFailure.CheckPay,
            ),
            (
                "once-per-round limit consumed",
                {"conditions": [Condition.LimitOncePerRound], "limit": False},
                False,
                None,
            ),
        )

        for name, state, expected, failure in rows:
            with self.subTest(name=name):
                checker, player, message = self.MakeChecker(
                    conditions=state.get("conditions", []),
                    need_cost=state.get("need_cost", False),
                )
                checker.UpdateLegalTargets.return_value = state.get(
                    "legal_targets",
                    True,
                )
                checker.HasCostTargets.return_value = state.get(
                    "cost_targets",
                    True,
                )
                checker.RequiresPayableResourceCost.return_value = state.get(
                    "need_cost",
                    False,
                )
                checker.cost_for_different_target.HasPayableTarget.return_value = \
                    state.get("payable", True)
                checker.effect.world.stat.IsOncePerRound.return_value = state.get(
                    "limit",
                    True,
                )

                self.assertEqual(
                    checker.CheckCondition(message, player),
                    expected,
                )

                if failure is not None:
                    checker.failures.Set.assert_called_with(player, failure)
                else:
                    checker.failures.SetText.assert_called_once()

    def test_source_location_matrix(self):
        rows = (
            ("player play area", {"in_play": True}, True),
            ("encounter play area", {"in_play": True}, True),
            ("processing", {"processing": True}, True),
            (
                "hand-only ability in hand",
                {"in_hand": True, "only_in_hand": True},
                True,
            ),
            ("ordinary action in hand", {"in_hand": True}, False),
            ("discard", {}, False),
            ("set aside", {}, False),
            ("face-up status area", {"status_area": True}, True),
            ("face-up boost ability in boost area", {"boost_area": True, "boost": True}, True),
        )

        for name, state, expected in rows:
            with self.subTest(name=name):
                flags = SimpleNamespace(
                    is_processing=state.get("processing", False),
                    is_status_area=state.get("status_area", False),
                    is_boost_area=state.get("boost_area", False),
                )
                face = Mock(name=name)
                face.card.area = SimpleNamespace(flags=flags)
                face.IsFaceUp.return_value = True
                face.IsThisFaceUp.return_value = True
                face.IsLikeInHand.return_value = state.get("in_hand", False)
                face.IsInPlay.return_value = state.get("in_play", False)
                face.CanResolveWhenRevealed.return_value = False
                ability = SimpleNamespace(
                    is_ignore_out_of_play=False,
                    can_work_also_in_hand=False,
                    can_work_only_in_hand=state.get("only_in_hand", False),
                    is_play=False,
                    flags=SimpleNamespace(
                        is_when_reveal=False,
                        is_boost=state.get("boost", False),
                    ),
                )
                checker = EffectChecker.__new__(EffectChecker)
                checker.effect = SimpleNamespace(this=face)
                checker.ability = ability

                with patch.object(Obligation, "IsType", return_value=False), \
                     patch.object(Villain, "IsType", return_value=False):
                    self.assertEqual(checker.CheckNotOutOfPlay(), expected)


if __name__ == "__main__":
    unittest.main()
