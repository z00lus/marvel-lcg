from . import *

# Kingpin's Henchman


def GetAbilities() -> Sequence['Ability']:
    return [
        AbilityFactory.UnitCannotTakeDamageWhile(
            AbilityType.NonKeyword,
            CardFinder(name="Kingpin"),
        ),
    ]
