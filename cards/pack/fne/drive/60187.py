from . import *


def GetAbilities() -> Sequence['Ability']:
    return [
        AbilityFactory.AttachToFaceWhenPutIntoPlay(
            NO_VEHICLE_ENEMY,
            highest_sch=True,
            if_cannot_gain_surge=True,
        ),
        VehicleDamageAbility(3),
    ]
