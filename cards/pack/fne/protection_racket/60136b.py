from . import *


def GetAbilities() -> Sequence['Ability']:
    def character_entered(effect: 'Effect', message: 'Message.AfterCardEnterPlay') -> None:
        character = message.trigger.CastTo(Unit2)
        character.TakeDamage(effect.this, 1, effect)
        PlaceThreatHere(effect)

    return [
        AbilityFactory.AfterCardEnterPlay(
            AbilityType.ForcedResponse,
            Unit2,
            character_entered,
        ),
    ]
