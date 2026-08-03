from . import *


def GetAbilities() -> Sequence['Ability']:
    return GetMissionFrontAbilities(protect_professor=True)
