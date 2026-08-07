from types import SimpleNamespace
import importlib
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

# Preserve the application's normal import ordering.
from engine import Engine

from game.ability.ability_type import AbilityType, TimingPriority
from game.card.face.attribute.can_boost import CanBoost
from game.card.face.model.face_on_event import ModelOnEvent
from game.event.manager import EventManager
from game.message import Message
from game.message.message import Message2
from game.message.message_type import CanBeInstead
from game.player.action.player_action import PlayerAction
from game.player.scenario import Scenario


ROOT = Path(__file__).resolve().parents[1]


class _EncounterQueue:

    def __init__(self, faces):
        self.faces = list(faces)

    def GetSize(self):
        return len(self.faces)

    def GetTop(self):
        return self.faces[0] if self.faces else None

    def Append(self, face):
        self.faces.append(face)

    def Remove(self, face):
        self.faces.remove(face)

    def DiscardAll(self, effect):
        self.faces.clear()


class V18EncounterChecklistTests(unittest.TestCase):

    def test_encounter_card_runs_one_reveal_lifecycle(self):
        area = SimpleNamespace(flags=SimpleNamespace(
            is_discards=False,
            is_removed=False,
            is_dealt_encounter=True,
            is_boost_area=False,
        ))
        event_manager = Mock()
        world = SimpleNamespace(
            is_game_over=False,
            main_schemes_deck=object(),
            area_revealing=object(),
            event_manager=event_manager,
        )
        player = SimpleNamespace(dealt_encounter_cards=object())
        face = Mock()
        face.card = SimpleNamespace(
            world=world,
            area=area,
            state=SimpleNamespace(is_revealing=False),
        )
        face.IsInDeck.return_value = False
        face.IsInPlay.return_value = False
        face.ResolveV17UniqueReveal.return_value = False
        face.OnPlayerRevealCard.return_value = True
        face.effect.RegisterTemp.return_value = []
        owner = SimpleNamespace(GetThis=lambda: face)
        would_reveal = SimpleNamespace(is_be_instead=False)
        reveal = SimpleNamespace(
            is_be_instead=False,
            cancel_all_effects=False,
            cancel_when_revealed=False,
            resolved=[],
        )
        revealed = object()

        with patch.object(
            Message,
            'WhenCardWouldReveal',
            return_value=would_reveal,
        ), patch.object(
            Message,
            'WhenPlayerRevealCard',
            return_value=reveal,
        ), patch.object(
            Message,
            'WhenCardRevealed',
            return_value=revealed,
        ) as revealed_factory, patch.object(
            Message,
            'AfterCardRevealedEnd',
            return_value=object(),
        ), patch(
            'game.card.face.base.EncounterNonVillainCard.IsType',
            return_value=False,
        ), patch(
            'game.card.face.card_type.MainScheme.IsType',
            return_value=False,
        ), patch(
            'game.ability.factory.AbilityFactory.WhenCardEnterPlay',
            return_value=object(),
        ), patch(
            'game.operate.faces.Faces.MoveAllTo',
        ), patch(
            'game.message.Message.AfterCardsMovedToRevealingArea_Text',
        ), patch(
            'game.operate.effects.Effects.UnRegister',
        ), patch('game.effect.rule.GameRule', return_value=object()):
            result = ModelOnEvent.Reveal(owner, player, object())

        self.assertIs(result, revealed)
        revealed_factory.assert_called_once_with(face, reveal)
        face.OnWhenCardRevealed.assert_called_once_with(revealed)
        event_manager.BeginRevealResponseDeferral.assert_called_once_with()
        event_manager.EndRevealResponseDeferral.assert_called_once_with()
        self.assertFalse(face.card.state.is_revealing)

    def test_boost_card_uses_boost_window_without_becoming_revealed(self):
        face = Mock()
        face.CountBoostIconsInternal.return_value = 3
        face.effect.Find.return_value = [SimpleNamespace(name='When Revealed')]
        boosting_area = object()
        world = SimpleNamespace(
            is_game_over=False,
            area_boosting=boosting_area,
        )
        face.card.area = object()
        deck = _EncounterQueue([face])
        attacker = SimpleNamespace(
            card=SimpleNamespace(world=world, game_area=object()),
            components=SimpleNamespace(
                boostable=SimpleNamespace(GetDeck=lambda: deck),
            ),
        )
        would_flip = Mock(is_be_instead=False)
        flip = Mock(cancel_boost_icons=False)
        become = Mock()
        after_become = Mock()
        callback = Mock()

        def move_to_boosting(faces, destination, effect):
            self.assertIs(destination, boosting_area)
            deck.Remove(face)
            face.card.area = boosting_area

        with patch.object(
            Message,
            'WhenBoostCardWouldTurnedFaceUp',
            return_value=would_flip,
        ), patch.object(
            Message,
            'WhenBoostCardTurnedFaceUp',
            return_value=flip,
        ), patch.object(
            Message,
            'WhenCardBecomeBoost',
            return_value=become,
        ), patch.object(
            Message,
            'AfterCardBecomeBoost',
            return_value=after_become,
        ), patch.object(
            Message,
            'WhenCardRevealed',
        ) as revealed_factory, patch.object(
            Message,
            'WhenPlayerRevealCard',
        ) as player_reveal_factory, patch(
            'game.card.face.base.EncounterNonVillainCard.IsType',
            return_value=True,
        ), patch(
            'game.operate.worlds.Worlds.GetAmplifyFaces',
            return_value=[],
        ), patch(
            'game.operate.faces.Faces.MoveAllTo',
            side_effect=move_to_boosting,
        ), patch(
            'game.message.Message.AfterCardsMovedToBoostingArea_Text',
        ), patch('game.operate.faces.Faces.DiscardAll'):
            CanBoost.ResolveBoostCards(attacker, object(), callback)

        callback.assert_called_once_with(face, 3)
        become.Send.assert_called_once_with()
        revealed_factory.assert_not_called()
        player_reveal_factory.assert_not_called()

    def test_surge_card_is_revealed_only_after_current_card_finishes(self):
        log = []
        first = Mock(name='first')
        surge = Mock(name='surge')
        queue = _EncounterQueue([first])
        player = SimpleNamespace(
            dealt_encounter_cards=queue,
            world=SimpleNamespace(is_game_over=False),
            is_eliminated=False,
            stat=SimpleNamespace(RecordReveal=lambda face: None),
            GetIdentity=lambda: object(),
        )
        action = SimpleNamespace(GetPlayer=lambda: player)

        def reveal_first(player, effect):
            queue.Remove(first)
            log.append('current reveal')
            queue.Append(surge)
            log.append('current responses complete')

        def reveal_surge(player, effect):
            queue.Remove(surge)
            log.append('surge reveal')

        first.Reveal.side_effect = reveal_first
        surge.Reveal.side_effect = reveal_surge

        with patch('game.effect.rule.GameRule', return_value=object()):
            PlayerAction.RevealEncounterCards(action)

        self.assertEqual(
            log,
            ['current reveal', 'current responses complete', 'surge reveal'],
        )

    def test_multiple_chained_surges_preserve_fifo_order(self):
        log = []
        first = Mock(name='first')
        second = Mock(name='second')
        third = Mock(name='third')
        queue = _EncounterQueue([first])
        player = SimpleNamespace(
            dealt_encounter_cards=queue,
            world=SimpleNamespace(is_game_over=False),
            is_eliminated=False,
            stat=SimpleNamespace(RecordReveal=lambda face: None),
            GetIdentity=lambda: object(),
        )
        action = SimpleNamespace(GetPlayer=lambda: player)

        def reveal(face, next_face=None):
            def operation(player, effect):
                queue.Remove(face)
                log.append(face._mock_name)
                if next_face:
                    queue.Append(next_face)
            return operation

        first.Reveal.side_effect = reveal(first, second)
        second.Reveal.side_effect = reveal(second, third)
        third.Reveal.side_effect = reveal(third)

        with patch('game.effect.rule.GameRule', return_value=object()):
            PlayerAction.RevealEncounterCards(action)

        self.assertEqual(log, ['first', 'second', 'third'])

    def test_minion_surge_finishes_reveal_before_quickstrike(self):
        class RevealMessage(Message2):
            pass

        class EngageMessage(Message2):
            pass

        world = SimpleNamespace(is_game_over=False, render=Mock())
        manager = EventManager(world)
        log = []

        def make_effect(name, message_type, priority, forced=True):
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

        surge = make_effect('Surge', RevealMessage, TimingPriority.Boost)
        quickstrike = make_effect(
            'Quickstrike',
            EngageMessage,
            TimingPriority.ForcedResponse,
        )
        manager.RegisterEffect(surge)
        manager.RegisterEffect(quickstrike)

        def make_message(message_type):
            message = object.__new__(message_type)
            message.world = world
            message.related_faces = set()
            return message

        def record(message, effects, priority, *args):
            log.extend(effect.name for effect in effects)
            return False

        with patch.object(
            manager,
            'ProcessForcedEffect',
            side_effect=record,
        ):
            manager.BeginRevealResponseDeferral()
            manager.BroadcastMessage(make_message(EngageMessage))
            manager.BroadcastMessage(make_message(RevealMessage))
            self.assertEqual(log, ['Surge'])
            manager.EndRevealResponseDeferral()

        self.assertEqual(log, ['Surge', 'Quickstrike'])

    def test_forced_response_resolves_before_optional_response(self):
        class ResponseMessage(Message2):
            pass

        world = SimpleNamespace(is_game_over=False)
        manager = EventManager(world)
        message = object.__new__(ResponseMessage)
        message.world = world
        message.related_faces = set()
        log = []

        def make_effect(name, priority, forced):
            return SimpleNamespace(
                name=name,
                is_unregister=False,
                is_local=False,
                is_nonkeyword=False,
                is_rule=False,
                is_forced=forced,
                priority=priority,
                ability=SimpleNamespace(
                    when=ResponseMessage,
                    flags=SimpleNamespace(
                        is_statistics=False,
                        is_temp=False,
                    ),
                ),
            )

        manager.RegisterEffect(make_effect(
            'Forced Response', TimingPriority.ForcedResponse, True,
        ))
        manager.RegisterEffect(make_effect(
            'Response', TimingPriority.Response, False,
        ))

        def record(prefix):
            return lambda message, effects, priority, *args: \
                log.extend(f'{prefix}:{effect.name}' for effect in effects) or False

        with patch.object(
            manager,
            'ProcessForcedEffect',
            side_effect=record('forced'),
        ), patch.object(
            manager,
            'ProcessOptionalEffect',
            side_effect=record('optional'),
        ):
            manager.BroadcastMessage(message)

        self.assertEqual(
            log,
            ['forced:Forced Response', 'optional:Response'],
        )

    def test_obligation_has_readable_choices_and_executes_each_result(self):
        module = importlib.import_module('cards.pack.core.spider_man.01165')
        ability = module.GetAbilities()[0]
        obligation = Mock()
        source = Mock()
        source.CastTo.return_value = obligation
        effect = SimpleNamespace(this=source)
        player = Mock()
        player.IsAlterEgo.return_value = True
        message = Mock()
        message.GetGaveToPlayer.return_value = player

        with patch.object(module, 'YouMayFlipToYourAlterEgoForm'), patch.object(
            module.Faces,
            'RemoveAllFromGame',
        ) as remove, patch.object(
            module.Faces,
            'DiscardAll',
        ) as discard:
            ability.operation(effect, message)
            choose_args = player.ChooseAbilities.call_args.args
            first, second = choose_args[1:]

            self.assertEqual(
                first.name,
                'Exhaust Peter Parker → remove Eviction Notice from the game',
            )
            self.assertEqual(
                second.name,
                'Discard 1 card at random from your hand. This card gains '
                'surge. Discard this obligation',
            )
            self.assertEqual(len(first.cost_funcs), 1)

            choice_effect = SimpleNamespace(
                targets=[],
                GetPaidResources=lambda: None,
            )
            first.operation(choice_effect, Mock())
            remove.assert_called_once_with([obligation], effect)

            second.operation(choice_effect, Mock())
            player.DiscardRandomHandCards.assert_called_once_with(1, effect)
            obligation.GainSurge.assert_called_once_with(1, effect)
            discard.assert_called_once_with([obligation], effect)

    def test_encounter_deck_reset_adds_one_acceleration_token(self):
        next_id = iter(range(1, 20))
        world = SimpleNamespace(
            object_manager=SimpleNamespace(
                AddObject=lambda category, obj: next(next_id),
            ),
        )
        scenario = Scenario('test', world)
        scheme = Mock()
        effect = object()
        rule = object()

        with patch(
            'game.operate.worlds.Worlds.FindMainScheme',
            return_value=scheme,
        ), patch('game.effect.rule.GameRule', return_value=rule):
            scenario.encounter_deck.process_after_shuffle(
                scenario.encounter_deck,
                effect,
            )

        scheme.PlaceAccelerationToken.assert_called_once_with(1, rule)

    def test_running_out_of_encounter_deck_requests_penalty_reshuffle(self):
        from game.rule.gameplay import GetGamePlayRules

        reset_rule = next(
            ability for ability in GetGamePlayRules()
            if ability.when is Message.AfterDeckRunOut
        )
        discard_pile = Mock()
        discard_pile.GetSize.return_value = 4
        deck = Mock(
            bind_discard_pile=discard_pile,
            flags=SimpleNamespace(is_player_deck=False),
        )
        effect = SimpleNamespace(
            world=SimpleNamespace(is_game_started=True),
        )

        reset_rule.operation(effect, SimpleNamespace(deck=deck))

        deck.ShuffleWithDiscardPile.assert_called_once_with(True, effect)


class V18InterruptResponseChecklistTests(unittest.TestCase):

    def MakeWorld(self):
        return SimpleNamespace(
            is_game_over=False,
            is_initializing=False,
            object_manager=SimpleNamespace(AddObject=lambda category, obj: 1),
            const_players=[],
        )

    def MakeEffect(self, name, message_type, ability_type, operation=None):
        if operation is None:
            operation = lambda message: None
        return SimpleNamespace(
            name=name,
            operation=operation,
            is_unregister=False,
            is_local=False,
            is_nonkeyword=False,
            is_rule=False,
            is_forced=ability_type.flags.is_forced,
            priority=ability_type.flags.GetPriority(),
            ability=SimpleNamespace(
                when=message_type,
                flags=ability_type.flags,
            ),
        )

    def MakeMessage(self, message_type, world):
        message = object.__new__(message_type)
        message.world = world
        message.related_faces = set()
        return message

    def test_interrupt_precedes_event_and_event_continues_before_response(self):
        class BeforeEvent(Message2):
            pass

        class AfterEvent(Message2):
            pass

        world = self.MakeWorld()
        manager = EventManager(world)
        log = []
        interrupt = self.MakeEffect(
            'interrupt', BeforeEvent, AbilityType.Interrupt,
            lambda message: log.append('interrupt'),
        )
        response = self.MakeEffect(
            'response', AfterEvent, AbilityType.Response,
            lambda message: log.append('response'),
        )
        manager.RegisterEffect(interrupt)
        manager.RegisterEffect(response)

        def process_optional(message, effects, local, priority):
            for effect in effects:
                effect.operation(message)
            return False

        with patch.object(
            manager,
            'ProcessOptionalEffect',
            side_effect=process_optional,
        ):
            manager.BroadcastMessage(self.MakeMessage(BeforeEvent, world))
            log.append('event')
            manager.BroadcastMessage(self.MakeMessage(AfterEvent, world))

        self.assertEqual(log, ['interrupt', 'event', 'response'])

    def test_canceling_interrupt_prevents_event_and_its_response(self):
        class BeforeEvent(CanBeInstead):
            pass

        class AfterEvent(Message2):
            pass

        world = self.MakeWorld()
        manager = EventManager(world)
        log = []
        interrupt = self.MakeEffect(
            'cancel', BeforeEvent, AbilityType.Interrupt,
            lambda message: setattr(message, 'be_instead_internal', True),
        )
        response = self.MakeEffect(
            'response', AfterEvent, AbilityType.Response,
            lambda message: log.append('response'),
        )
        manager.RegisterEffect(interrupt)
        manager.RegisterEffect(response)
        before = BeforeEvent(world=world)

        def process_optional(message, effects, local, priority):
            for effect in effects:
                effect.operation(message)
            return False

        with patch.object(
            manager,
            'ProcessOptionalEffect',
            side_effect=process_optional,
        ):
            manager.BroadcastMessage(before)
            if not before.is_be_instead:
                log.append('event')
                manager.BroadcastMessage(self.MakeMessage(AfterEvent, world))

        self.assertTrue(before.is_be_instead)
        self.assertEqual(log, [])

    def test_forced_interrupt_is_processed_without_a_pass_choice(self):
        world = self.MakeWorld()
        first_player = Mock()
        world.GetFirstPlayer = lambda: first_player
        manager = EventManager(world)
        face = SimpleNamespace(card=object())
        effect = SimpleNamespace(
            this=face,
            priority=TimingPriority.ForcedInterrupt,
            ability=SimpleNamespace(flags=SimpleNamespace(
                is_resource=False,
                is_discard_pay=False,
                is_check_pay=False,
                is_delay_ability=False,
            )),
            context=SimpleNamespace(
                targets_internal=[],
                all_legal_targets=[],
            ),
            IsPlayerInitiator=lambda: False,
        )

        with patch.object(
            EventManager,
            'FilterAvailableEffects',
            side_effect=lambda message, effects, player, check_world, undo: effects,
        ), patch.object(manager, 'ProcessEffect') as process:
            manager.ProcessForcedEffect(
                SimpleNamespace(),
                [effect],
                TimingPriority.ForcedInterrupt,
                None,
            )

        process.assert_called_once_with(
            effect,
            unittest.mock.ANY,
            TimingPriority.ForcedInterrupt,
        )
        first_player.ChoiceAndSpellEffect.assert_not_called()

    def test_response_window_closes_after_player_passes(self):
        effect = SimpleNamespace(
            object_id=1,
            this=Mock(),
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

        with patch.object(
            EventManager,
            'FilterAvailableEffects',
            return_value=[effect],
        ) as available, patch(
            'game.event.manager.JobManager.Simultaneous',
            side_effect=lambda fn, players: [fn(p) for p in players],
        ):
            manager.ProcessOptionalEffect(
                SimpleNamespace(world=world),
                [effect],
                [],
                TimingPriority.Response,
            )

        available.assert_called_once()
        player.ChoiceAndSpellEffect.assert_called_once()

    def test_response_window_closes_after_selected_response_completes(self):
        effect = SimpleNamespace(
            object_id=1,
            this=Mock(),
            ability=SimpleNamespace(
                flags=SimpleNamespace(is_forced_action=False),
            ),
        )
        player = Mock()
        player.ChoiceAndSpellEffect.return_value = (effect, False)
        world = SimpleNamespace(
            const_players=[player],
            is_game_over=False,
        )
        manager = EventManager.__new__(EventManager)
        manager.world = world
        manager.new_effect_created = False

        with patch.object(
            EventManager,
            'FilterAvailableEffects',
            side_effect=[[effect], []],
        ) as available, patch(
            'game.event.manager.JobManager.Simultaneous',
            side_effect=lambda fn, players: [fn(p) for p in players],
        ):
            manager.ProcessOptionalEffect(
                SimpleNamespace(world=world),
                [effect],
                [],
                TimingPriority.Response,
            )

        self.assertEqual(available.call_count, 2)
        player.ChoiceAndSpellEffect.assert_called_once()


class V18InterruptResponseUiContractTests(unittest.TestCase):

    def test_valid_response_selection_enables_guarded_ok_button(self):
        effect_source = (
            ROOT / 'public/js/marvel/effect.ts'
        ).read_text(encoding='utf-8')
        ok_source = (
            ROOT / 'public/js/marvel/btn_ok.ts'
        ).read_text(encoding='utf-8')
        button_source = (
            ROOT / 'public/js/marvel/buttons.ts'
        ).read_text(encoding='utf-8')

        self.assertIn("BtnOk.setOk('Ok')", effect_source)
        self.assertIn('BtnOk.btn_ok_div.disabled = false', ok_source)
        self.assertIn(
            'BtnOk.btn_ok_div.disabled || SelectStep.isCard()',
            button_source,
        )
        self.assertIn('Button.doPost()', button_source)


if __name__ == '__main__':
    unittest.main()
