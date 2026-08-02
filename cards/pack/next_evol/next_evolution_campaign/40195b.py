from . import *


def GetAbilities() -> Sequence['Ability']:
    return [
        *AbilityFactory.GiveKeywordToInPlayWhenApplyThis(
            Hero,
            defense=1,
            retaliate=1,
        ),
    ]
