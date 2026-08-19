from . import *


def GetAbilities() -> Sequence['Ability']:

    def revealed(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        player = message.GetToPlayer()
        villain = Worlds.FindVillain(effect)
        art = Search.EncounterCard(
            effect,
            player,
            include_discard_pile=True,
            finder=ART,
        )
        if villain and art:
            art.AttachTo2(villain, effect)
        else:
            MoveArtToVillain(effect, player)

    def boost(effect: 'Effect', message: 'Message.WhenCardBecomeBoost') -> None:
        MoveArtToVillain(effect, message.GetToPlayer())

    return [
        AbilityFactory.WhenThisRevealed(None, revealed),
        AbilityFactory.WhenCardBecomeBoost("This", boost),
    ]
