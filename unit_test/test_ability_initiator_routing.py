from contextlib import ExitStack
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

# Preserve the application's normal import ordering.
from engine import Engine

from game.ability.ability_type import AbilityType
from game.card.face.base import Scheme2
from game.card.face.card_type import (
    Attachment,
    Environment,
    Minion,
    Obligation,
)
from game.event.manager import EventManager
from game.message import Message
from game.player import Player


ENCOUNTER_TYPES = {
    "attachment": Attachment,
    "minion": Minion,
    "scheme": Scheme2,
    "environment": Environment,
}


class AbilityInitiatorRoutingTests(unittest.TestCase):

    def MakePlayer(self, name: str) -> Player:
        player = object.__new__(Player)
        player.name = name
        return player

    def MakeMessage(self, message_type, player: Player):
        message = object.__new__(message_type)
        message.to_player = player
        return message

    def MakeEffect(
        self,
        message_type,
        *,
        source_kind: str="player",
        controller=None,
        area_owner=None,
        gave_to=None,
        in_play: bool=True,
        ability_type: AbilityType=AbilityType.Action,
        any_player: bool=False,
        choose: bool=False,
        forced: bool=False,
        blank: bool=False,
        removed: bool=False,
        obligations_area: bool=False,
    ):
        area = SimpleNamespace(
            flags=SimpleNamespace(
                is_obligations_area=obligations_area,
                is_removed=removed,
            ),
            GetOwner=lambda: area_owner,
        )
        source = SimpleNamespace(
            source_kind=source_kind,
            card=SimpleNamespace(area=area),
            is_treat_as_if_blank=blank,
            GetControlByOrOwner=lambda: controller,
            GetGaveToPlayer=lambda: gave_to,
            IsInPlay=lambda: in_play,
        )
        ability = SimpleNamespace(
            any_player_can_trigger_this_when=[lambda effect: True] if any_player else [],
            flags=ability_type.flags,
            ignore=SimpleNamespace(
                be_removed=False,
                treat_as_if_blank=False,
            ),
            is_choose=choose,
            is_play=False,
            when=message_type,
        )
        return SimpleNamespace(
            ability=ability,
            failures=Mock(),
            is_forced=forced,
            is_unregister=False,
            this=source,
        )

    def Filter(self, message, effect, asked_player, current_player):
        world = SimpleNamespace(GetCurrentPlayer=lambda: current_player)
        with ExitStack() as stack:
            for source_kind, source_type in ENCOUNTER_TYPES.items():
                stack.enter_context(patch.object(
                    source_type,
                    "IsType",
                    side_effect=lambda face, kind=source_kind:
                        face.source_kind == kind,
                ))
            return EventManager.SimpleCheckEffects(
                message,
                [effect],
                asked_player,
                world,
                None,
            )

    def test_encounter_actions_are_routed_to_the_active_player(self):
        active = self.MakePlayer("Active")
        scenario = SimpleNamespace(name="Scenario")
        message = self.MakeMessage(Message.WhenPlayerInTurn, active)

        for source_kind in ENCOUNTER_TYPES:
            with self.subTest(source_kind=source_kind):
                effect = self.MakeEffect(
                    Message.WhenPlayerInTurn,
                    source_kind=source_kind,
                    controller=scenario,
                    area_owner=scenario,
                )

                self.assertEqual(
                    self.Filter(message, effect, active, active),
                    [effect],
                )

    def test_encounter_action_is_not_routed_to_an_inactive_player(self):
        active = self.MakePlayer("Active")
        inactive = self.MakePlayer("Inactive")
        scenario = SimpleNamespace(name="Scenario")
        message = self.MakeMessage(Message.WhenPlayerInTurn, active)
        effect = self.MakeEffect(
            Message.WhenPlayerInTurn,
            source_kind="scheme",
            controller=scenario,
            area_owner=scenario,
        )

        self.assertEqual(self.Filter(message, effect, inactive, active), [])
        effect.failures.SetText.assert_called_once()

    def test_player_card_in_play_is_routed_to_its_controller(self):
        controller = self.MakePlayer("Controller")
        other = self.MakePlayer("Other")
        message = self.MakeMessage(Message.WhenPlayerInTurn, controller)
        effect = self.MakeEffect(
            Message.WhenPlayerInTurn,
            controller=controller,
            area_owner=other,
            in_play=True,
        )

        self.assertEqual(
            self.Filter(message, effect, controller, controller),
            [effect],
        )
        self.assertEqual(self.Filter(message, effect, other, controller), [])

    def test_player_card_out_of_play_is_routed_to_the_area_owner(self):
        owner = self.MakePlayer("Hand owner")
        stale_controller = self.MakePlayer("Stale controller")
        message = self.MakeMessage(Message.WhenPlayerInTurn, owner)
        effect = self.MakeEffect(
            Message.WhenPlayerInTurn,
            controller=stale_controller,
            area_owner=owner,
            in_play=False,
        )

        self.assertEqual(self.Filter(message, effect, owner, owner), [effect])
        self.assertEqual(
            self.Filter(message, effect, stale_controller, owner),
            [],
        )

    def test_obligation_in_obligations_area_is_routed_to_its_recipient(self):
        recipient = self.MakePlayer("Recipient")
        active = self.MakePlayer("Active")
        message = self.MakeMessage(Message.WhenPlayerInTurn, active)
        effect = self.MakeEffect(
            Message.WhenPlayerInTurn,
            source_kind="obligation",
            area_owner=SimpleNamespace(name="Scenario"),
            gave_to=recipient,
            obligations_area=True,
        )

        with patch.object(
            Obligation,
            "IsType",
            side_effect=lambda face: face.source_kind == "obligation",
        ):
            self.assertEqual(
                EventManager.SimpleCheckEffects(
                    message,
                    [effect],
                    recipient,
                    SimpleNamespace(GetCurrentPlayer=lambda: active),
                    None,
                ),
                [effect],
            )

    def test_obligation_in_play_is_routed_to_the_active_player(self):
        active = self.MakePlayer("Active")
        recipient = self.MakePlayer("Recipient")
        message = self.MakeMessage(Message.WhenPlayerInTurn, active)
        effect = self.MakeEffect(
            Message.WhenPlayerInTurn,
            source_kind="obligation",
            area_owner=SimpleNamespace(name="Scenario"),
            gave_to=recipient,
            obligations_area=False,
        )

        with patch.object(
            Obligation,
            "IsType",
            side_effect=lambda face: face.source_kind == "obligation",
        ):
            self.assertEqual(
                EventManager.SimpleCheckEffects(
                    message,
                    [effect],
                    active,
                    SimpleNamespace(GetCurrentPlayer=lambda: active),
                    None,
                ),
                [effect],
            )

    def test_any_player_ability_uses_the_trigger_message_player(self):
        active = self.MakePlayer("Active")
        owner = self.MakePlayer("Owner")
        message = self.MakeMessage(Message.WhenPlayerInTurn, active)
        effect = self.MakeEffect(
            Message.WhenPlayerInTurn,
            controller=owner,
            area_owner=owner,
            any_player=True,
        )

        self.assertEqual(self.Filter(message, effect, active, active), [effect])

    def test_resource_effect_is_routed_to_the_paying_player(self):
        payer = self.MakePlayer("Payer")
        other = self.MakePlayer("Other")
        message = self.MakeMessage(Message.WhenPlayerPayingResources, payer)
        effect = self.MakeEffect(
            Message.WhenPlayerPayingResources,
            controller=other,
            area_owner=other,
            ability_type=AbilityType.Resource,
        )

        self.assertEqual(self.Filter(message, effect, payer, other), [effect])
        self.assertEqual(self.Filter(message, effect, other, other), [])

    def test_forced_effect_does_not_require_an_optional_initiator(self):
        active = self.MakePlayer("Active")
        unrelated = self.MakePlayer("Unrelated")
        message = self.MakeMessage(Message.WhenPlayerInTurn, active)
        effect = self.MakeEffect(
            Message.WhenPlayerInTurn,
            controller=unrelated,
            area_owner=unrelated,
            forced=True,
        )

        self.assertEqual(self.Filter(message, effect, active, active), [effect])

    def test_blank_and_removed_sources_are_filtered_before_routing(self):
        active = self.MakePlayer("Active")
        message = self.MakeMessage(Message.WhenPlayerInTurn, active)

        for state in ("blank", "removed"):
            with self.subTest(state=state):
                effect = self.MakeEffect(
                    Message.WhenPlayerInTurn,
                    controller=active,
                    area_owner=active,
                    blank=state == "blank",
                    removed=state == "removed",
                )

                self.assertEqual(
                    self.Filter(message, effect, active, active),
                    [],
                )
                effect.failures.Set.assert_called_once()


if __name__ == "__main__":
    unittest.main()
