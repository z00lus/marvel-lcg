from . import *


def GetAbilities() -> Sequence['Ability']:
    return AbilityFactory.GiveKeywordToInPlayWhenApplyThis(Minion, health=2)
