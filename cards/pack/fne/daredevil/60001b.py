from . import *

# * Matt Murdock


def GetAbilities() -> Sequence['Ability']:
    return [
        AbilityFactory.BeginGameWithSetAside(
            SENSE_CARD_IDS,
            SetupSenseDeck,
        ),
        *ReturnSenseCardsToDeck(),
        *AbilityFactory.PlayWithTopCardOfDeckFaceup(
            lambda effect: [deck] if (deck := GetSenseDeck(effect.GetInitiator())) else [],
            ex_operation=RevealSenseDeck,
        ),
    ]
