from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

# Preserve the application's normal import ordering.
from engine import Engine

from game.ability.ability_type import AbilityType, TimingPriority
from game.event.manager import EventManager
from game.message import Message
from game.message.message import Message2
from game.world.world_rule import WorldRule


class V18TimingPriorityTests(unittest.TestCase):

    V18_PRIORITIES = {
        AbilityType.NonKeyword: TimingPriority.Constant,
        AbilityType.Status: TimingPriority.Status,
        AbilityType.ForcedInterrupt: TimingPriority.ForcedInterrupt,
        AbilityType.Interrupt: TimingPriority.Interrupt,
        AbilityType.Boost: TimingPriority.Boost,
        AbilityType.WhenRevealed: TimingPriority.Boost,
        AbilityType.WhenDefeated: TimingPriority.ForcedInterrupt,
        AbilityType.WhenCompleted: TimingPriority.ForcedInterrupt,
        AbilityType.ForcedResponse: TimingPriority.ForcedResponse,
        AbilityType.Response: TimingPriority.Response,
        AbilityType.Consequential: TimingPriority.Consequential,
    }

    def MakeRule(self, *rules: str) -> WorldRule:
        rule = WorldRule()
        rule.SetRule(list(rules), is_puzzle=False, seed=1)
        return rule

    def test_runtime_uses_v18_priority_for_every_relevant_ability_type(self):
        rule = self.MakeRule()

        for ability_type, expected in self.V18_PRIORITIES.items():
            with self.subTest(ability_type=ability_type):
                self.assertEqual(ability_type.flags.GetPriority(rule), expected)

    def test_status_replacement_precedes_other_forced_interrupts(self):
        rule = self.MakeRule('v18_all')

        priorities = [
            AbilityType.Status.flags.GetPriority(rule),
            AbilityType.ForcedInterrupt.flags.GetPriority(rule),
            AbilityType.Interrupt.flags.GetPriority(rule),
        ]

        self.assertEqual(
            priorities,
            [
                TimingPriority.Status,
                TimingPriority.ForcedInterrupt,
                TimingPriority.Interrupt,
            ],
        )
        self.assertEqual(priorities, sorted(priorities, key=lambda value: value.value))

    def test_event_manager_registers_the_ruleset_aware_effect_priority(self):
        world = SimpleNamespace()
        manager = EventManager(world)
        ability = SimpleNamespace(
            when=Message.WhenPlayerInTurn,
            priority=TimingPriority.Boost,
            flags=SimpleNamespace(
                is_statistics=False,
                is_temp=False,
            ),
        )
        effect = SimpleNamespace(
            is_unregister=False,
            is_local=False,
            is_nonkeyword=False,
            is_rule=False,
            is_forced=True,
            ability=ability,
            priority=TimingPriority.ForcedInterrupt,
        )

        manager.RegisterEffect(effect)

        self.assertEqual(
            manager.FindEffectsList(
                'Forced',
                Message.WhenPlayerInTurn,
                TimingPriority.ForcedInterrupt,
            ),
            [effect],
        )
        self.assertEqual(
            manager.FindEffectsList(
                'Forced',
                Message.WhenPlayerInTurn,
                TimingPriority.Boost,
            ),
            [],
        )

    def test_event_pipeline_processes_status_before_forced_interrupt(self):
        class TimingTestMessage(Message2):
            pass

        world = SimpleNamespace(is_game_over=False)
        manager = EventManager(world)
        message = object.__new__(TimingTestMessage)
        message.world = world
        message.related_faces = set()

        def make_effect(priority: TimingPriority):
            return SimpleNamespace(
                is_unregister=False,
                is_local=False,
                is_nonkeyword=False,
                is_rule=False,
                is_forced=True,
                priority=priority,
                ability=SimpleNamespace(
                    when=TimingTestMessage,
                    priority=TimingPriority.Normal,
                    flags=SimpleNamespace(
                        is_statistics=False,
                        is_temp=False,
                    ),
                ),
            )

        status = make_effect(TimingPriority.Status)
        forced_interrupt = make_effect(TimingPriority.ForcedInterrupt)
        manager.RegisterEffect(forced_interrupt)
        manager.RegisterEffect(status)
        processed_priorities = []

        with patch.object(
            manager,
            'ProcessForcedEffect',
            side_effect=lambda message, effects, priority, undo: processed_priorities.append(priority) or False,
        ):
            manager.BroadcastMessage(message)

        self.assertEqual(
            processed_priorities,
            [TimingPriority.Status, TimingPriority.ForcedInterrupt],
        )

    def test_solo_player_can_order_simultaneous_forced_responses(self):
        first_player = Mock()
        world = SimpleNamespace(
            is_game_over=False,
            GetFirstPlayer=lambda: first_player,
        )
        manager = EventManager(world)

        def make_effect(name: str):
            face = SimpleNamespace(name=name, card=object())
            return SimpleNamespace(
                this=face,
                priority=TimingPriority.ForcedResponse,
                ability=SimpleNamespace(
                    flags=SimpleNamespace(
                        is_resource=False,
                        is_discard_pay=False,
                        is_check_pay=False,
                        is_delay_ability=False,
                    ),
                ),
                context=SimpleNamespace(
                    targets_internal=[],
                    all_legal_targets=[],
                ),
                IsPlayerInitiator=lambda: False,
            )

        first = make_effect('first')
        second = make_effect('second')
        effects = [first, second]
        first_player.AskChooseFace.return_value = second.this
        processed = []

        with patch.object(
            EventManager,
            'FilterAvailableEffects',
            side_effect=lambda message, available, player, check_world, undo: available,
        ), patch.object(
            manager,
            'ProcessEffect',
            side_effect=lambda effect, message, priority: processed.append(effect),
        ):
            manager.ProcessForcedEffect(
                SimpleNamespace(),
                effects,
                TimingPriority.ForcedResponse,
                None,
            )

        self.assertEqual(processed, [second, first])
        first_player.AskChooseFace.assert_called_once()


if __name__ == '__main__':
    unittest.main()
