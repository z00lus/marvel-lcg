from . import *


def GetAbilities() -> Sequence['Ability']:

    def revealed(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        this = effect.this.CastTo(Villain)
        Find.FindAndAttachTo(
            effect,
            this,
            who_perform=message.GetToPlayer(),
            name="Adamantium-Laced Spine",
            card_type=Attachment,
        )

    return [
        AbilityFactory.WhenThisRevealed(None, revealed),
        BullseyeActivationAbility(),
    ]
