from . import *


def GetAbilities() -> Sequence['Ability']:
    return [
        ElectroWhenRevealed("2*"),
        ElectroSchemeAbility(1),
    ]
