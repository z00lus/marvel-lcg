from . import *

# Medical Officer's Aid

def GetAbilities() -> Sequence['Ability']:

    def medical_officers_aid(effect: 'Effect', message: 'Message.AfterCardPlacedCounter') -> None:
        this = effect.this.CastTo(Attachment)
        Unused(this)

        player = Worlds.GetFirstPlayer(effect)
        player.ChooseAbilities(
            effect,
            AbilityFactory.ForChoiceAbility(
                "Heal 2 damage from the villain",
                lambda targets:
                    this.HealthUnits(targets, 2, effect)
            ).SetTarget(Villain, canbe_heal=True),
            AbilityFactory.ForChoiceAbility(
                "Deal 1 damage to the friendly character with the fewest remaining hit points",
                lambda targets:
                    this.DealDamage(targets, 1, effect)
            ).SetTarget(Friend, fewest_remaining_hp=True)
        )


    return [
        AbilityFactory.AttachToFaceWhenPutIntoPlay(
            Villain
        ),
        AbilityFactory.AfterCounterPlacedOn(
            AbilityType.ForcedResponse,
            "This",
            'secret',
            medical_officers_aid
        ),
        IfThereAre3BoardMemberAttachmentsInPlayPlayersLoseTheGame(),
        IfThereAre3BoardMemberAttachmentsInPlayAfterThisEntersPlay(),
    ]
