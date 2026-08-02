from . import *


# Magneto's Power

def GetAbilities() -> Sequence['Ability']:
    return [
        AbilityFactory.AttachToFaceWhenPutIntoPlay(
            CardFinder(name="Magneto", card_type=Villain),
        ),
    ]
