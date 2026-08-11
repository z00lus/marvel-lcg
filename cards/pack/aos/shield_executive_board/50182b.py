from . import *

# Surveillance Officer's Aid

def GetAbilities() -> Sequence['Ability']:

    def surveillance_officers_aid(effect: 'Effect', message: 'Message.AfterCardPlacedCounter') -> None:
        this = effect.this.CastTo(Attachment)
        Unused(this)

        this.PlaceThreatOnSchemes("MainScheme", 2, effect)


    return [
        AbilityFactory.AttachToFaceWhenPutIntoPlay(
            Villain
        ),
        AbilityFactory.AfterCounterPlacedOn(
            AbilityType.ForcedResponse,
            "This",
            'secret',
            surveillance_officers_aid
        ),
        IfThereAre3BoardMemberAttachmentsInPlayPlayersLoseTheGame(),
        IfThereAre3BoardMemberAttachmentsInPlayAfterThisEntersPlay(),
    ]
