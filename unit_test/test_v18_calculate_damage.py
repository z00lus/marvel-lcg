from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

# Preserve the application's normal import ordering.
from engine import Engine

from game.card.face.attribute.can_attack import AttackProperty, CanAttack
from game.card.face.attribute.can_defense import CanDefense
from game.ability.ability_type import TimingPriority
from game.event.manager import EventManager
from game.message import Message
from game.message.message_type import NoSendResolve


class V18CalculateDamageTests(unittest.TestCase):

    def MakeMessage(self, attack, defense):
        world = SimpleNamespace(
            is_game_over=False,
            object_manager=SimpleNamespace(AddObject=lambda category, obj: 1),
        )
        attacker = Mock()
        attacker.card.world = world
        attacker.CastTo.return_value = attacker
        target = Mock()
        target.card.world = world
        broad_attack = SimpleNamespace(defender=None)
        attack_unit = SimpleNamespace(would_atk_message=broad_attack)
        message = Message.WhenCalculateAttackDamage(
            attacker,
            target,
            attack,
            defense,
            [],
            attack_unit,
        )
        return message, attacker, target, attack_unit

    def test_undefended_calculation_uses_modified_attack_damage(self):
        message, attacker, _, _ = self.MakeMessage(5, 0)
        effect = SimpleNamespace()

        with patch('game.card.face.base.Unit2.IsType', return_value=True):
            message.IncreaseDamage(2, effect)

        self.assertEqual(message.base_attack_damage, 5)
        self.assertEqual(message.attack_damage, 7)
        self.assertEqual(message.calculated_damage, 7)
        attacker.GainForThisActive.assert_called_once()

    def test_defense_is_applied_once_after_attack_modifiers(self):
        message, _, _, _ = self.MakeMessage(5, 2)

        self.assertEqual(message.attack_damage, 5)
        self.assertEqual(message.calculated_damage, 3)
        self.assertEqual(message.calculated_damage, 3)

    def test_defense_cannot_reduce_calculated_damage_below_zero(self):
        message, _, _, _ = self.MakeMessage(2, 4)

        self.assertEqual(message.calculated_damage, 0)

    def test_calculate_damage_is_a_real_event_window(self):
        message, _, _, _ = self.MakeMessage(3, 0)

        self.assertNotIsInstance(message, NoSendResolve)
        self.assertTrue(message.send_resolve_message)

    def test_interrupts_can_modify_the_explicit_calculate_damage_window(self):
        message, _, _, _ = self.MakeMessage(3, 0)
        manager = EventManager(message.world)
        effect = SimpleNamespace(
            is_unregister=False,
            is_local=False,
            is_nonkeyword=False,
            is_rule=False,
            is_forced=True,
            priority=TimingPriority.Interrupt,
            ability=SimpleNamespace(
                when=Message.WhenCalculateAttackDamage,
                flags=SimpleNamespace(
                    is_statistics=False,
                    is_temp=False,
                ),
            ),
        )
        manager.RegisterEffect(effect)

        with patch.object(
            manager,
            'ProcessForcedEffect',
            return_value=False,
        ) as process:
            manager.BroadcastMessage(message)

        process.assert_called_once_with(
            message,
            [effect],
            TimingPriority.Interrupt,
            None,
        )

    def test_card_effect_can_declare_exhausted_character_without_exhausting_again(self):
        being_attacked = SimpleNamespace(
            DeclareDefenderInternal=Mock(),
        )
        defender = Mock()
        defender.IsExhausted.return_value = True
        effect = object()

        with patch.object(CanDefense, 'IsType', return_value=True):
            Message.WhenUnitBeingAttack.DeclareDefender(
                being_attacked,
                defender,
                effect,
            )

        being_attacked.DeclareDefenderInternal.assert_called_once_with(
            defender,
            effect,
            being_attacked,
            True,
        )
        defender.BasicDefense.assert_called_once_with(being_attacked, effect)

    def test_attack_stops_before_damage_when_solo_player_is_eliminated(self):
        player = SimpleNamespace(is_eliminated=True)
        attack = AttackProperty(against_player=player)

        with patch(
            'game.operate.worlds.Worlds.IsGameOver',
            return_value=False,
        ):
            self.assertFalse(
                CanAttack.CanContinueToDealAttackDamage(attack, object())
            )

    def test_attack_can_deal_damage_while_solo_player_remains_active(self):
        player = SimpleNamespace(is_eliminated=False)
        attack = AttackProperty(against_player=player)

        with patch(
            'game.operate.worlds.Worlds.IsGameOver',
            return_value=False,
        ):
            self.assertTrue(
                CanAttack.CanContinueToDealAttackDamage(attack, object())
            )


if __name__ == '__main__':
    unittest.main()
