from . import *

# Coordinated Effort


def GetAbilities() -> Sequence['Ability']:
    return [
        AbilityFactory.CanPlayThisUpgradeCard(EncounterCard),
    ]
