from . import *

# * Simon Williams


def GetAbilities() -> Sequence['Ability']:
    return [
        AbilityFactory.SetupPutIntoPlay(["58002"]),
    ]
