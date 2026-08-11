from . import *

# Tactical Officer's Aid

def GetAbilities() -> Sequence['Ability']:

    def tactical_officers_aid(effect: 'Effect', message: 'Message.AfterCardPlacedCounter') -> None:
        this = effect.this.CastTo(Attachment)
        Unused(this)

        player = Worlds.GetFirstPlayer(effect)

        player.ChooseAbilities(
            effect,
            AbilityFactory.ForChoiceAbility(
                "Deal 2 damage to a friendly character",
                lambda targets:
                    this.DealDamage(targets, 2, effect)
            ).SetTarget(Friend)
        )

    return [
        AbilityFactory.AttachToFaceWhenPutIntoPlay(
            Villain
        ),
        AbilityFactory.AfterCounterPlacedOn(
            AbilityType.ForcedResponse,
            "This",
            'secret',
            tactical_officers_aid
        ),
        IfThereAre3BoardMemberAttachmentsInPlayPlayersLoseTheGame(),
        IfThereAre3BoardMemberAttachmentsInPlayAfterThisEntersPlay(),
    ]
