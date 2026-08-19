from . import *


def GetAbilities() -> Sequence['Ability']:
    def revealed(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        Unused(message)
        charge = FindElectricCharge(effect)
        if charge:
            Faces.PlaceCountersOn([charge], "3*", 'charge', effect)

    return [
        AbilityFactory.WhenThisRevealed(None, revealed),
        ElectroSchemeAbility(2),
    ]
