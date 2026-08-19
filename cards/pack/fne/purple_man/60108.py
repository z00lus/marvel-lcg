from . import *


def GetAbilities() -> Sequence['Ability']:
    return [
        *AbilityFactory.GiveKeywordToInPlayWhenApplyThis(
            Minion,
            trait="INFLUENCED",
        ),
        PurpleManBoostAbility(),
    ]
