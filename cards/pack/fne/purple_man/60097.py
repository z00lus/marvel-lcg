from . import *


def GetAbilities() -> Sequence['Ability']:
    return [*PurpleManKeywords(guard=1)]
