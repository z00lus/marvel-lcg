from . import *


def GetAbilities() -> Sequence['Ability']:
    return AbilityFactory.GiveKeywordToInPlayWhenApplyThis(Minion, guard=1)
