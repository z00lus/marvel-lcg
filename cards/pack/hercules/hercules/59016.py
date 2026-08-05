from . import *


def GetAbilities() -> Sequence['Ability']:
    return [
        *AbilityFactory.GiveKeywordToAttached(
            "You",
            thwart=1,
            attack=1,
            defense=1,
        ),
    ]
