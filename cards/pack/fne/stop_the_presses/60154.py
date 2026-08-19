from . import *


def GetAbilities() -> Sequence['Ability']:

    def betty_brant(
        effect: 'Effect',
        message: 'Message.WhenBoostCardTurnedFaceUp',
    ) -> None:
        message.CancelAllBoostIcons(effect)
        message.CancelBoostAbility(effect)
        activating_enemy = message.would_message.trigger.CastTo(Enemy)
        Faces.GiveFacedownBoostCards([activating_enemy], 1, effect)

    return [
        AbilityFactory.WhenBoostCardTurnedFaceUp(
            AbilityType.Interrupt,
            None,
            betty_brant,
        ).SetCostFunc(CostFunc.Exhaust("This"))
        .SetCostFunc(CostFunc.Counter("This", 1, STAMINA)),
    ]
