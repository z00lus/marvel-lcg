from . import *
from cards.pack.aoa.campaign import GetOverseerAbilities


def GetAbilities() -> Sequence['Ability']:
    return GetOverseerAbilities()
