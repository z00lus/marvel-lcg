from . import *


def GetAbilities() -> Sequence['Ability']:
    def revealed(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        for player in Worlds.GetPlayers(effect):
            player.GetIdentity().TakeDamage(effect.this, 1, effect)

    return [
        MaryDefeatReplacement("13*"),
        AbilityFactory.WhenThisRevealed(None, revealed),
    ]
