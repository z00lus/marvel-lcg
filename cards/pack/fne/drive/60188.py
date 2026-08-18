from . import *


def GetAbilities() -> Sequence['Ability']:
    return [
        AbilityFactory.AttachToFaceWhenPutIntoPlay(
            NO_VEHICLE_ENEMY,
            fewest_remaining_hp=True,
            if_cannot_gain_surge=True,
        ),
        VehicleDamageAbility(6),
    ]
