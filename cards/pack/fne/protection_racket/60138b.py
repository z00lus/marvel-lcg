from . import *


def GetAbilities() -> Sequence['Ability']:
    def character_defeated(effect: 'Effect', message: 'Message.AfterUnitDefeatedUnit') -> None:
        if Unit2.IsType(message.killer):
            message.killer.CastTo(Unit2).HealHealth(1, effect)
        PlaceThreatHere(effect)

    def scheme_defeated(effect: 'Effect', message: 'Message.AfterUnitDefeatedScheme') -> None:
        if Unit2.IsType(message.killer):
            message.killer.CastTo(Unit2).HealHealth(1, effect)
        PlaceThreatHere(effect)

    return [
        AbilityFactory.AfterUnitDefeatedUnit(
            AbilityType.ForcedResponse,
            Unit2,
            Unit2,
            character_defeated,
        ),
        AbilityFactory.AfterUnitDefeatedScheme(
            AbilityType.ForcedResponse,
            Unit2,
            Scheme2,
            scheme_defeated,
        ),
    ]
