from . import *

# * Daredevil


def GetAbilities() -> Sequence['Ability']:

    def is_top_of_sense_deck(effect: 'Effect', message: 'Message.CheckIfFaceIsLikeInHand') -> bool:
        deck = GetSenseDeck(effect.GetInitiator())
        return bool(deck and deck.GetTop() == message.which_face)

    return [
        *AbilityFactory.YouMayPlayCardLikeInHand(
            AbilityType.NonKeyword,
            CardFinder(trait="SENSE"),
            conditions=[is_top_of_sense_deck],
        ),
        *ReturnSenseCardsToDeck(),
        *AbilityFactory.PlayWithTopCardOfDeckFaceup(
            lambda effect: [deck] if (deck := GetSenseDeck(effect.GetInitiator())) else [],
            ex_operation=RevealSenseDeck,
        ),
    ]
