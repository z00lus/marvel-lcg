from . import *


def GetAbilities() -> Sequence['Ability']:
    return [
        AbilityFactory.AttachToFaceWhenPutIntoPlay(
            NO_VEHICLE_ENEMY,
            highest_atk=True,
            if_cannot_gain_surge=True,
        ),
        VehicleDamageAbility(4),
    ]
