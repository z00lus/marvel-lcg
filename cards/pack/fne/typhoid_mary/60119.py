from . import *


def GetAbilities() -> Sequence['Ability']:
    def give_tough(effect: 'Effect', villain: 'Villain|None') -> None:
        if villain:
            Faces.GiveStatus([villain], "Tough", effect)

    def revealed(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        give_tough(effect, Worlds.FindVillain(effect))

    def boost(effect: 'Effect', message: 'Message.WhenCardBecomeBoost') -> None:
        if IsActivatingMary(message, "Bloody Mary"):
            give_tough(effect, message.activating_enemy.CastTo(Villain))

    return [
        AbilityFactory.WhenThisRevealed(None, revealed),
        AbilityFactory.WhenCardBecomeBoost("This", boost),
    ]
