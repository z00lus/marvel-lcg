from . import *

# Legal Trouble


def GetAbilities() -> Sequence['Ability']:
    return [
        AbilityFactory.ReduceCostToPlayThis(
            1,
            your_identity_has_traits=["ATTORNEY", "POLICE"],
        ),
        AbilityFactory.CanPlayThisUpgradeCard(Minion),
        *AbilityFactory.GiveKeywordToAttached(
            Minion,
            scheme=-2,
        ),
    ]
