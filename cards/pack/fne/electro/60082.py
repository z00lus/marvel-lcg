from . import *


def GetAbilities() -> Sequence['Ability']:
    def defeated(effect: 'Effect', message: 'Message.WhenSchemeBeDefeated') -> None:
        Unused(message)
        charge = FindElectricCharge(effect)
        if charge:
            Faces.PlaceCountersOn([charge], 3, 'charge', effect)

    return [
        AbilityFactory.WhenSchemeBeDefeated(
            AbilityType.WhenDefeated,
            "This",
            defeated,
        ),
    ]
