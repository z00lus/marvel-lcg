from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

# Preserve the application's normal import ordering.
from engine import Engine

from game.ability.ability_type import TimingPriority
from game.event.manager import EventManager
from game.message import Message
from game.message.message import Message2


class RevealLifecycleTests(unittest.TestCase):

    def MakeManager(self):
        world = SimpleNamespace(is_game_over=False, render=Mock())
        return EventManager(world)

    def MakeMessage(self, message_type):
        message = object.__new__(message_type)
        message.world = self.manager.world
        message.related_faces = set()
        return message

    def MakeEffect(self, name, message_type, priority, *, forced=True):
        return SimpleNamespace(
            name=name,
            is_unregister=False,
            is_local=False,
            is_nonkeyword=False,
            is_rule=False,
            is_forced=forced,
            priority=priority,
            ability=SimpleNamespace(
                when=message_type,
                flags=SimpleNamespace(
                    is_statistics=False,
                    is_temp=False,
                ),
            ),
        )

    def setUp(self):
        self.manager = self.MakeManager()
        self.log = []

        def record(prefix):
            def action(message, effects, priority, *args):
                self.log.extend(f'{prefix}:{effect.name}' for effect in effects)
                return False
            return action

        self.process_patches = [
            patch.object(
                self.manager,
                'ProcessRuleEffect',
                side_effect=record('rule'),
            ),
            patch.object(
                self.manager,
                'ProcessForcedEffect',
                side_effect=record('forced'),
            ),
            patch.object(
                self.manager,
                'ProcessOptionalEffect',
                side_effect=record('optional'),
            ),
        ]
        for process_patch in self.process_patches:
            process_patch.start()

    def tearDown(self):
        for process_patch in reversed(self.process_patches):
            process_patch.stop()

    def test_when_revealed_resolves_before_quickstrike_and_normal_response(self):
        quickstrike = self.MakeEffect(
            'Quickstrike',
            Message.AfterMinionEngagePlayer,
            TimingPriority.ForcedResponse,
        )
        when_revealed = self.MakeEffect(
            'Printed When Revealed',
            Message.WhenCardRevealed,
            TimingPriority.Boost,
        )
        response = self.MakeEffect(
            'After reveal response',
            Message.AfterCardRevealed,
            TimingPriority.Response,
            forced=False,
        )
        for effect in (quickstrike, when_revealed, response):
            self.manager.RegisterEffect(effect)

        self.manager.BeginRevealResponseDeferral()
        self.manager.BroadcastMessage(
            self.MakeMessage(Message.AfterMinionEngagePlayer)
        )
        self.manager.BroadcastMessage(
            self.MakeMessage(Message.WhenCardRevealed)
        )
        self.manager.BroadcastMessage(
            self.MakeMessage(Message.AfterCardRevealed)
        )

        self.assertEqual(self.log, ['forced:Printed When Revealed'])

        self.manager.EndRevealResponseDeferral()

        self.assertEqual(
            self.log,
            [
                'forced:Printed When Revealed',
                'forced:Quickstrike',
                'optional:After reveal response',
            ],
        )

    def test_incite_and_surge_resolve_inside_reveal_before_responses(self):
        for name in ('Incite', 'Surge'):
            self.manager.RegisterEffect(self.MakeEffect(
                name,
                Message.WhenCardRevealed,
                TimingPriority.Boost,
            ))
        self.manager.RegisterEffect(self.MakeEffect(
            'Response',
            Message.WhenCardRevealed,
            TimingPriority.Response,
            forced=False,
        ))

        self.manager.BeginRevealResponseDeferral()
        self.manager.BroadcastMessage(
            self.MakeMessage(Message.WhenCardRevealed)
        )

        self.assertEqual(self.log, ['forced:Incite', 'forced:Surge'])

        self.manager.EndRevealResponseDeferral()

        self.assertEqual(
            self.log,
            ['forced:Incite', 'forced:Surge', 'optional:Response'],
        )

    def test_nested_reveal_flushes_its_responses_before_outer_reveal_resumes(self):
        class OuterResponse(Message2):
            pass

        class InnerResponse(Message2):
            pass

        self.manager.RegisterEffect(self.MakeEffect(
            'outer',
            OuterResponse,
            TimingPriority.ForcedResponse,
        ))
        self.manager.RegisterEffect(self.MakeEffect(
            'inner',
            InnerResponse,
            TimingPriority.ForcedResponse,
        ))

        self.manager.BeginRevealResponseDeferral()
        self.manager.BroadcastMessage(self.MakeMessage(OuterResponse))

        self.manager.BeginRevealResponseDeferral()
        self.manager.BroadcastMessage(self.MakeMessage(InnerResponse))
        self.assertEqual(self.log, [])

        self.manager.EndRevealResponseDeferral()
        self.assertEqual(self.log, ['forced:inner'])

        self.manager.EndRevealResponseDeferral()
        self.assertEqual(self.log, ['forced:inner', 'forced:outer'])

    def test_reveal_response_queue_is_closed_even_when_flushing_raises(self):
        class ResponseMessage(Message2):
            pass

        self.manager.RegisterEffect(self.MakeEffect(
            'response',
            ResponseMessage,
            TimingPriority.ForcedResponse,
        ))
        self.manager.BeginRevealResponseDeferral()
        self.manager.BroadcastMessage(self.MakeMessage(ResponseMessage))

        forced_process_patch = self.process_patches.pop(1)
        forced_process_patch.stop()
        with patch.object(
            self.manager,
            'ProcessForcedEffect',
            side_effect=RuntimeError('test failure'),
        ), patch(
            'game.event.manager.Log.OnCrash',
            return_value='failure info',
        ) as on_crash:
            self.manager.EndRevealResponseDeferral()

        self.assertEqual(self.manager.reveal_response_queues, [])
        on_crash.assert_called_once()
        self.manager.world.render.ErrorOccurred.assert_called_once_with(
            'failure info'
        )


if __name__ == '__main__':
    unittest.main()
