from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

# Match the application's normal import order without initializing the server.
from engine import Engine

from game.card.card import Card
from game.card.face.card_type import Ally, Event, Support, Upgrade
from game.operate.faces import Faces
from game.player.player import Player


def Flags(**values):
    defaults = {
        "is_in_play": False,
        "is_in_hand": False,
        "is_player_deck": False,
        "is_encounter_deck": False,
        "is_discards": False,
        "is_boost_area": False,
        "is_side_scheme_area": False,
    }
    defaults.update(values)
    return SimpleNamespace(**defaults)


class Area:
    def __init__(self, owner, *, bind_card=None, bind_discard_pile=None, **flags):
        self.owner = owner
        self.bind_card = bind_card
        self.bind_discard_pile = bind_discard_pile
        self.flags = Flags(**flags)

    def GetOwner(self):
        return self.owner


def MakePlayer(name):
    player = object.__new__(Player)
    player.name = name
    player.is_scenario = False
    player.is_eliminated = False
    player.allies = object()
    player.supports = object()
    player.area_hero = object()
    player.hand_cards = object()
    player.player_deck = object()
    player.discard_pile = object()
    return player


def MakeScenario():
    scenario = SimpleNamespace(
        name="Scenario",
        is_scenario=True,
        is_eliminated=False,
        encounter_deck=object(),
        encounter_discard_pile=object(),
    )
    return scenario


def MakeFace(face_type, *, desc=None):
    face = object.__new__(face_type)
    face.paper = SimpleNamespace(desc=desc or {})
    face.consider_as = SimpleNamespace(card_types={})
    return face


def MakeCard(face, owner, area, *, v17=True, players=None):
    card = object.__new__(Card)
    card.face = face
    face.card = card
    card.owner_original = owner
    card.owner_internal = owner
    card.controller_internal = None
    card.area = area
    card.bind_discard_pile = None
    scenario = MakeScenario()
    card.world = SimpleNamespace(
        rule=SimpleNamespace(v17_ownership_control=v17),
        players=list(players or []),
        area_removed=object(),
        GetScenario=lambda: scenario,
    )
    return card


class OwnershipModelTests(unittest.TestCase):

    def test_original_owner_does_not_change_with_game_owner(self):
        original = MakePlayer("Original")
        new_owner = MakePlayer("Campaign owner")
        card = MakeCard(
            MakeFace(Support),
            original,
            Area(original, is_in_play=False),
            players=[original, new_owner],
        )

        card.SetOwner(new_owner)

        self.assertIs(card.GetOriginalOwner(), original)
        self.assertIs(card.GetOwner(), new_owner)

    def test_scenario_player_card_changes_owner_when_control_is_taken(self):
        scenario = MakeScenario()
        player = MakePlayer("Player")
        card = MakeCard(
            MakeFace(Support),
            scenario,
            Area(scenario, is_in_play=False),
            players=[player],
        )
        card.world.GetScenario = lambda: scenario

        card.TakeControl(player)

        self.assertIs(card.GetOwner(), player)
        self.assertIs(card.controller_internal, player)
        self.assertIs(card.GetOriginalOwner(), scenario)

    def test_taking_control_of_normal_player_card_does_not_change_owner(self):
        owner = MakePlayer("Owner")
        controller = MakePlayer("Controller")
        card = MakeCard(
            MakeFace(Ally),
            owner,
            Area(owner, is_in_play=False),
            players=[owner, controller],
        )

        card.TakeControl(controller)

        self.assertIs(card.GetOwner(), owner)
        self.assertIs(card.controller_internal, controller)

    def test_campaign_card_changes_owner_between_players(self):
        original = MakePlayer("Original campaign owner")
        controller = MakePlayer("New campaign owner")
        card = MakeCard(
            MakeFace(Support, desc={"Class": "Campaign;Basic"}),
            original,
            Area(original, is_in_play=False),
            players=[original, controller],
        )

        card.TakeControl(controller)

        self.assertIs(card.GetOwner(), controller)

    def test_linked_card_changes_game_owner(self):
        scenario = MakeScenario()
        player = MakePlayer("Player")
        card = MakeCard(
            MakeFace(Upgrade, desc={"Linked": "Specialized Training"}),
            scenario,
            Area(scenario, is_in_play=False),
            players=[player],
        )

        card.TakeControl(player)

        self.assertIs(card.GetOwner(), player)


class ControllerTests(unittest.TestCase):

    def test_v17_player_controls_cards_in_their_out_of_play_area(self):
        player = MakePlayer("Player")
        card = MakeCard(
            MakeFace(Event),
            player,
            Area(player, is_in_hand=True),
            players=[player],
        )

        self.assertIs(card.GetController(), player)

    def test_foreign_card_in_players_hand_uses_that_player_as_controller(self):
        owner = MakePlayer("Owner")
        hand_player = MakePlayer("Hand player")
        face = MakeFace(Event)
        card = MakeCard(
            face,
            owner,
            Area(hand_player, is_in_hand=True),
            players=[owner, hand_player],
        )

        self.assertIs(face.GetControlByPlayer(), hand_player)

    def test_upgrade_follows_other_players_control_of_attached_card(self):
        owner = MakePlayer("Owner")
        controller = MakePlayer("Controller")
        host = Mock()
        host.GetController.return_value = controller
        card = MakeCard(
            MakeFace(Upgrade),
            owner,
            Area(owner, bind_card=host, is_in_play=True),
            players=[owner, controller],
        )

        self.assertIs(card.GetController(), controller)

    def test_player_upgrade_on_scenario_card_remains_owner_controlled(self):
        owner = MakePlayer("Owner")
        scenario = MakeScenario()
        host = Mock()
        host.GetController.return_value = scenario
        card = MakeCard(
            MakeFace(Upgrade),
            owner,
            Area(scenario, bind_card=host, is_in_play=True),
            players=[owner],
        )

        self.assertIs(card.GetController(), owner)

    def test_player_card_in_special_scenario_area_can_be_under_no_player_control(self):
        owner = MakePlayer("Owner")
        scenario = MakeScenario()
        card = MakeCard(
            MakeFace(Ally),
            owner,
            Area(scenario, is_in_play=True),
            players=[owner],
        )

        self.assertIs(card.GetController(), scenario)

    def test_change_control_moves_ally_without_resetting_state(self):
        owner = MakePlayer("Owner")
        controller = MakePlayer("Controller")
        card = MakeCard(
            MakeFace(Ally),
            owner,
            Area(owner, is_in_play=True),
            players=[owner, controller],
        )
        card.state = SimpleNamespace(
            is_ready=False,
            damage=3,
            statuses=["Tough"],
            attachments=["Upgrade"],
        )
        before = vars(card.state).copy()
        effect = Mock()

        with patch.object(Card, "MoveToArea", return_value=True) as move:
            card.ChangeControl(controller, effect)

        move.assert_called_once_with(controller.allies, effect)
        self.assertIs(card.controller_internal, controller)
        self.assertEqual(vars(card.state), before)

    def test_control_reverts_to_owner_when_effect_ends(self):
        owner = MakePlayer("Owner")
        controller = MakePlayer("Controller")
        card = MakeCard(
            MakeFace(Ally),
            owner,
            Area(controller, is_in_play=True),
            players=[owner, controller],
        )
        card.controller_internal = controller
        effect = Mock()

        with patch.object(Card, "MoveToArea", return_value=True) as move:
            card.RevertControl(effect)

        self.assertIsNone(card.controller_internal)
        move.assert_called_once_with(owner.allies, effect)


class OwnerDestinationTests(unittest.TestCase):

    def test_leaving_play_for_another_hand_uses_owners_hand(self):
        owner = MakePlayer("Owner")
        controller = MakePlayer("Controller")
        card = MakeCard(
            MakeFace(Ally),
            owner,
            Area(controller, is_in_play=True),
            players=[owner, controller],
        )
        other_hand = Area(controller, is_in_hand=True)

        self.assertIs(card.GetOwnerEquivalentArea(other_hand), owner.hand_cards)

    def test_card_whose_owner_left_the_game_is_removed(self):
        owner = MakePlayer("Owner")
        card = MakeCard(
            MakeFace(Ally),
            owner,
            Area(owner, is_in_play=True),
            players=[],
        )

        self.assertIs(
            card.GetOwnerEquivalentArea(Area(owner, is_discards=True)),
            card.world.area_removed,
        )

    def test_played_foreign_event_uses_its_owners_discard(self):
        owner = MakePlayer("Owner")
        controller = MakePlayer("Controller")
        processing = Area(controller)
        card = MakeCard(
            MakeFace(Event),
            owner,
            processing,
            players=[owner, controller],
        )

        self.assertIs(card.GetDefaultDiscardArea(processing), owner.discard_pile)

    def test_cosmic_entity_resolved_as_boost_uses_encounter_discard(self):
        owner = MakePlayer("Owner")
        scenario = MakeScenario()
        boosting = Area(scenario, is_boost_area=True)
        card = MakeCard(
            MakeFace(Event),
            owner,
            boosting,
            players=[owner],
        )
        card.world.GetScenario = lambda: scenario

        self.assertIs(
            card.GetDefaultDiscardArea(boosting),
            scenario.encounter_discard_pile,
        )

    def test_special_deck_keeps_its_bound_discard_pile(self):
        owner = MakePlayer("Owner")
        special_discard = object()
        source = Area(owner)
        card = MakeCard(
            MakeFace(Event),
            owner,
            source,
            players=[owner],
        )
        card.bind_discard_pile = special_discard

        self.assertIs(card.GetDefaultDiscardArea(source), special_discard)


class PermanentAttachmentTests(unittest.TestCase):

    def MakePermanent(self):
        owner = MakeScenario()
        face = Mock()
        face.permanent = True
        face.GetOwner.return_value = owner
        face.card.area = object()
        return face

    def test_permanent_attachment_resolves_attach_to_again(self):
        face = self.MakePermanent()
        former_host = Mock()
        new_host = Mock()
        new_host.card.IsOnField.return_value = True
        new_host.GetControlBy.return_value = MakeScenario()
        player = MakePlayer("First Player")

        attach_effect = Mock()
        attach_effect.context.initiator = MakeScenario()

        def reattach(effect, message):
            face.bind_face = new_host

        attach_effect.ability.operation.side_effect = reattach
        face.effect.Find.return_value = [attach_effect]

        with patch(
                "game.card.face.attribute.has_permanent.HasPermanent.IsType",
                return_value=True,
             ), patch(
                "game.operate.worlds.Worlds.GetFirstPlayer",
                return_value=player,
             ), patch(
                "game.message.Message.WhenCardPutIntoPlay",
                return_value=Mock(),
             ), patch.object(Faces, "RemoveAllFromGame") as remove:
            result = Faces.ResolvePermanentAttachmentAfterHostLeaves(
                face,
                former_host,
                Mock(),
            )

        self.assertTrue(result)
        remove.assert_not_called()

    def test_permanent_attachment_without_valid_target_is_removed(self):
        face = self.MakePermanent()
        face.bind_face = None
        face.effect.Find.return_value = []

        with patch(
                "game.card.face.attribute.has_permanent.HasPermanent.IsType",
                return_value=True,
             ), patch.object(Faces, "RemoveAllFromGame") as remove:
            result = Faces.ResolvePermanentAttachmentAfterHostLeaves(
                face,
                Mock(),
                Mock(),
            )

        self.assertFalse(result)
        remove.assert_called_once()


class EliminationOwnershipTests(unittest.TestCase):

    def test_foreign_cards_use_owner_discard_and_permanents_are_removed(self):
        eliminated = MakePlayer("Eliminated")
        other = MakePlayer("Owner")
        ordinary = Mock()
        ordinary.GetOwner.return_value = other
        permanent = Mock()
        permanent.GetOwner.return_value = other
        permanent.permanent = True
        eliminated.allies = SimpleNamespace(GetAll=lambda: [ordinary])
        eliminated.supports = SimpleNamespace(GetAll=lambda: [permanent])
        eliminated.obligations_area = SimpleNamespace(GetAll=lambda: [])
        rule = Mock()

        def is_permanent(face):
            return face is permanent

        with patch(
                "game.card.face.attribute.has_permanent.HasPermanent.IsType",
                side_effect=is_permanent,
             ), patch.object(Faces, "DiscardAll") as discard, patch.object(
                Faces,
                "RemoveAllFromGame",
             ) as remove, patch(
                "game.effect.rule.GameRule",
                return_value=Mock(),
             ):
            eliminated._DiscardForeignCardsForV17Elimination(rule)

        discard.assert_called_once_with([ordinary], rule, into_area="Owner")
        remove.assert_called_once()


if __name__ == "__main__":
    unittest.main()
