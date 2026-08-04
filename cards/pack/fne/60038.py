from . import *

# Innate Reflexes


def GetAbilities() -> Sequence['Ability']:
    return [
        *AbilityFactory.GiveKeywordToAttached(
            "You",
            defense=1,
        ),
    ]
