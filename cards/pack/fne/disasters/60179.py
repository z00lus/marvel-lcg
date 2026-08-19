from . import *


def GetAbilities() -> Sequence['Ability']:
    return DisasterEnvironmentAbilities("RR", bonus_tough=True)
