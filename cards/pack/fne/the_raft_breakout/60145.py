from . import *
from game.ability.factory.treat import TreatAsMinion


def GetAbilities() -> Sequence['Ability']:

    def revealed(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        player = message.GetToPlayer()
        allies = [
            ally for ally in player.GetControlAllies()
            if ally.GetCounters('threat') == 0
        ]
        if not allies:
            return
        ally = allies[0] if len(allies) == 1 else player.AskChooseFace(allies, effect)
        if not ally:
            return
        Faces.PlaceCountersOn([ally], 1, 'threat', effect)
        TreatAsMinion(ally, "Deceived Minion", player, effect)

    return [AbilityFactory.WhenThisRevealed(None, revealed)]
