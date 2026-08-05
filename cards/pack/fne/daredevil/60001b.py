from . import *

# * Matt Murdock


def GetAbilities() -> Sequence['Ability']:

    def return_sense_to_deck(effect: 'Effect', message: 'Message.WhenCardWouldLeavePlay') -> None:
        deck = GetSenseDeck(effect.GetInitiator())
        if not deck or message.into_area == deck:
            return

        message.SetBeInstead(effect)
        Faces.MoveAllToDeck([message.trigger], deck, "Bottom", effect)

    return [
        AbilityFactory.BeginGameWithSetAside(
            SENSE_CARD_IDS,
            SetupSenseDeck,
        ),
        AbilityFactory.WhenCardWouldLeavePlay(
            AbilityType.ForcedInterrupt,
            CardFinder(trait="SENSE"),
            return_sense_to_deck,
            conditions=[
                lambda effect, message:
                    message.trigger.GetOwnerPlayer() == effect.GetInitiator()
            ],
        ),
    ]
