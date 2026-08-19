from . import *


def GetAbilities() -> Sequence['Ability']:
    def revealed(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        player = message.GetToPlayer()
        Faces.ExhaustAll(player.GetControlUpgrade(), effect)

    def controls_attached_identity(
        effect: 'Effect',
        message: 'Message.WhenCardWouldReady',
    ) -> bool:
        this = effect.this.CastTo(Attachment)
        return this.GetBindFace().GetControlByPlayer() == message.trigger.GetControlByPlayer()

    def would_ready(effect: 'Effect', message: 'Message.WhenCardWouldReady') -> None:
        this = effect.this.CastTo(Attachment)
        player = message.trigger.GetControlByPlayer()
        if player.AskSpendResources(Cost("Y", or_cost=Cost("2")), effect):
            Faces.RemoveCountersOn([this], 1, 'drain', effect)
        else:
            message.SetBeInstead(effect)

    return [
        AbilityFactory.AttachToFaceWhenPutIntoPlay("YourIdentity"),
        AbilityFactory.WhenThisRevealed(None, revealed),
        AbilityFactory.WhenCardWouldReady(
            AbilityType.ForcedInterrupt,
            Upgrade,
            would_ready,
            control_by="AnyPlayer",
            conditions=[controls_attached_identity],
        ),
    ]
