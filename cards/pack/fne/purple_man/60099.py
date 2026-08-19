from . import *


def GetAbilities() -> Sequence['Ability']:
    return [*PurpleManKeywords(guard=1, patrol=1, villainous=1)]
