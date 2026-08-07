from importlib import import_module
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

# Preserve the application's normal import ordering.
from engine import Engine

from game.ability.condition.card_type import ConditionCardType
from game.card.card_finder import CardFinder
from game.selector.selector_filter import SelectorFilter


class V18ReferentialTargetingTests(unittest.TestCase):

    def MakeFilter(self, *effect_checks):
        finder = Mock(spec=CardFinder)
        finder.Check.return_value = True
        selector_filter = SelectorFilter(
            finder,
            affects_target_if=effect_checks,
        )
        effect = SimpleNamespace(initiator=Mock())
        face = Mock()
        face.card = Mock()
        return selector_filter, finder, effect, face

    def test_target_is_legal_when_any_declared_effect_can_affect_it(self):
        selector_filter, finder, effect, face = self.MakeFilter(
            lambda effect, face: False,
            lambda effect, face: True,
        )

        result = selector_filter.FilterLegalTargets([face], effect)

        self.assertEqual(result, [face])
        finder.Check.assert_called_once_with(face, effect)

    def test_target_is_illegal_when_no_declared_effect_can_affect_it(self):
        selector_filter, _, effect, face = self.MakeFilter(
            lambda effect, face: False,
            lambda effect, face: False,
        )

        self.assertEqual(selector_filter.FilterLegalTargets([face], effect), [])

    def test_effect_alternatives_do_not_bypass_independent_restrictions(self):
        selector_filter, _, effect, face = self.MakeFilter(
            lambda effect, face: True,
        )
        # Attack, thwart, Crisis, control, and similar requirements are added
        # as independent checks and must remain conjunctive.
        selector_filter.AddParameter(
            check_effect_fn=lambda effect, face: False,
        )

        self.assertEqual(selector_filter.FilterLegalTargets([face], effect), [])

    def test_effect_alternatives_do_not_bypass_crisis_thwart_restriction(self):
        module = import_module('cards.pack.msm.ms_marvel.05004')
        ability = module.GetAbilities()[0]
        selector_filter = ability.selectors[0].selector_filter
        selector_filter.affects_target_if = (lambda effect, face: True,)
        selector_filter.finder.Check = Mock(return_value=True)
        scheme = Mock()
        scheme.card = Mock()
        scheme.threat = 1
        scheme.IsDefeated.return_value = False
        scheme.CanBeThwartBy.return_value = False
        effect = SimpleNamespace(
            this=Mock(),
            initiator=Mock(),
            world=SimpleNamespace(rule=SimpleNamespace()),
        )

        with patch('game.card.face.base.Scheme2.IsType', return_value=True), \
             patch('game.card.face.card_type.Event.IsType', return_value=True):
            result = selector_filter.FilterLegalTargets([scheme], effect)

        self.assertEqual(result, [])
        scheme.CanBeThwartBy.assert_called_once_with(effect)

    def test_already_confused_or_stalwart_enemy_remains_valid_for_damage(self):
        target = Mock()
        target.CanbeConfused.return_value = False
        target.IsDefeated.return_value = False
        target.GetBuff.return_value = None

        with patch('game.card.face.base.Unit2.IsType', return_value=True):
            checks = (
                ConditionCardType.TargetCanBeConfused,
                ConditionCardType.TargetCanTakeDamage,
            )
            self.assertFalse(checks[0](Mock(), target))
            self.assertTrue(checks[1](Mock(), target))

    def test_enemy_immune_to_both_parts_is_not_a_valid_target(self):
        target = Mock()
        target.CanbeConfused.return_value = False
        target.IsDefeated.return_value = False
        target.GetBuff.return_value = object()

        with patch('game.card.face.base.Unit2.IsType', return_value=True):
            checks = (
                ConditionCardType.TargetCanBeConfused,
                ConditionCardType.TargetCanTakeDamage,
            )
            self.assertFalse(any(check(Mock(), target) for check in checks))

    def test_concussive_blow_and_tackle_declare_both_target_effects(self):
        modules = (
            ('cards.pack.msm.05015', ConditionCardType.TargetCanBeStunned),
            ('cards.pack.msm.05031', ConditionCardType.TargetCanBeConfused),
            ('cards.pack.psylocke.41014', ConditionCardType.TargetCanBeConfused),
        )

        for module_name, status_check in modules:
            with self.subTest(module=module_name):
                ability = import_module(module_name).GetAbilities()[0]
                selector_filter = ability.selectors[0].selector_filter
                self.assertEqual(
                    selector_filter.affects_target_if,
                    (status_check, ConditionCardType.TargetCanTakeDamage),
                )
                # These are attack events. Their CanBeAttackBy check remains a
                # separate mandatory condition outside the OR effect list.
                self.assertGreaterEqual(len(selector_filter.check_effect_fns), 1)

    def test_explicit_then_instruction_still_requires_first_part_to_succeed(self):
        module = import_module('cards.pack.drs.invocation.09035')
        ability = module.GetAbilities()[0]
        source = Mock()
        source.CastTo.return_value = source
        unit = Mock()
        unit.CanbeConfused.return_value = False
        unit.CanGainTough.return_value = False
        unit.CanbeStunned.return_value = True
        status_target = Mock()
        status_card = Mock()
        status_card.GetBindFace.return_value = status_target
        selected = Mock()
        selected.GetBindFace.return_value.CastTo.return_value = unit
        selected.CastTo.return_value = status_card
        player = Mock()
        player.DeclareStatusCard.return_value = 'Stunned'
        effect = SimpleNamespace(
            this=source,
            targets=[selected],
            GetInitiator=lambda: player,
        )

        with patch.object(module.Faces, 'GiveStatus', return_value=0), \
             patch.object(module.Faces, 'DiscardAll') as discard, \
             patch.object(module, 'PlaceThisCardInInvocationDeckDiscardPile'):
            ability.operation(effect, Mock())

        discard.assert_not_called()


if __name__ == '__main__':
    unittest.main()
