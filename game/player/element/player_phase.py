from core import *
from game.card.face import *
from game.ability import *
from game.message import *
from game.player import *

class PlayerPhase:

    def __init__(self, player: 'Player') -> None:
        self.player = player

    ################################################################################
    # Phase
    def MayDiscardHandCardsAndDrawUpToMax(self, display_name: str, message: 'Message2'):
        from game.effect.rule import GameRule
        player = self.player
        faces = player.hand_cards.Get()

        value = len(player.GetCountHandSizeFaces()) - player.hand_size
        value = value if value >= 0 else 0

        rule = GameRule(player.GetIdentity(), message, display_name=display_name)
        player.AskDiscardFaces(faces, (value, "All"), rule)
        player.DrawUp("Max", rule)

    def ResolveMulligans(self, message: 'Message.WhenPlayerResolveMulligans') -> None:
        self.MayDiscardHandCardsAndDrawUpToMax("Resolve Mulligans", message)

    def BeginPhase(self) -> None:
        player = self.player
        player.stat.OnBeginPhase()

    def BeginTurn(self) -> None:
        player = self.player
        player.controller.manager.OnBeginTurn()
        player.stat.OnBeginTurn()
        return

    def PlayerTurn(self) -> None:
        from game.message import Message

        player = self.player
        world = player.world

        player.controller.manager.OnPlayerTurnStart()

        turn_begin_message = Message.WhenPlayerTurnBegin(player)
        turn_begin_message.Send()
        begin_message = Message.AfterPlayerTurnBegin(player, turn_begin_message)
        begin_message.Send()

        if player.is_eliminated:
            return

        message = Message.WhenPlayerInTurn(player, world.round_id)
        message.Send()
        if player.is_eliminated:
            return

        turn_end_message = Message.WhenPlayerTurnEnd(player, world.round_id)
        turn_end_message.Send()
        if player.is_eliminated:
            return
        player.res_pool.Reset()
        end_message = Message.AfterPlayerTurnEnd(player, turn_end_message)
        end_message.Send()

    def EndTurn(self):
        player = self.player
        player.stat.OnEndTurn()

    # TODO: use trigger to rewrite?
    def EndPhase(self) -> None:
        from game.card.face.card_face import CardFace
        from game.card.face.base import EncounterCard
        from game.effect.rule import EndPhase
        from game.operate.faces import Faces
        from game.operate.worlds import Worlds

        player = self.player
        message = Message.WhenPlayerEndPhase(player)
        message.Send()

        self.MayDiscardHandCardsAndDrawUpToMax("End Phase", message)

        if player.is_eliminated:
            return

        faces: List[CardFace] = []
        effect = EndPhase(player)
        for face in player.GetControlCards():
            faces.append(face)
            for upgrade in face.GetInventoryDeck().Get():
                faces.append(upgrade)

        # Encounter cards are not controlled by a player, but the end of the
        # player phase readies exhausted cards in play regardless of owner.
        # Do this once for a multiplayer game; each player still readies their
        # own cards through the existing loop above.
        if player == player.world.GetFirstPlayer():
            faces += [
                face for face in Worlds.GetOnFieldCards(player.GetIdentity().card.game_area)
                if EncounterCard.IsType(face)
            ]
        Faces.ReadyAll(faces, effect)

        self.player.has_change_form = False
        player.stat.OnEndPhase()

        return

    def BeginRound(self) -> None:
        player = self.player
        player.stat.OnBeginRound()

    def EndRound(self) -> None:
        player = self.player
        player.stat.OnEndRound()
