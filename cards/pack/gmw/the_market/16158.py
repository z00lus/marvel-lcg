from . import *

# Close Call

def GetAbilities() -> Sequence['Ability']:

    def close_call(effect: 'Effect', message: 'Message.WhenBoostCardTurnedFaceUp') -> None:
        this = effect.this.CastTo(Event)
        Unused(this)

        message.CancelBoostAbility(effect)
        message.CancelAllBoostIcons(effect)

        Faces.DiscardAll([message.trigger], effect)

        initiator = effect.GetInitiator()
        initiator.DrawUp(1, effect)


    return [
        AbilityFactory.WhenBoostCardTurnedFaceUp(
            AbilityType.HeroInterrupt,
            None,
            close_call
        ).SetPlay().SetLabel()
        .SetHasNoTargetEffect(),
    ]
