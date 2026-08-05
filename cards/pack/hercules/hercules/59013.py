from . import *


def GetAbilities() -> Sequence['Ability']:

    def gauntlets(effect: 'Effect', message: 'Message.WhenUnitWouldDefend') -> None:
        gifts = CountGifts(effect.GetInitiator())
        if gifts:
            message.trigger.GainForThisActive(
                effect,
                message.would_atk_message,
                retaliate=gifts,
            )

    return [
        AbilityFactory.WhenUnitDefendAgainstAttack(
            AbilityType.HeroInterrupt,
            CardFinder(name="Hercules", card_type=Hero),
            gauntlets,
        ).SetCostFunc(CostFunc.Exhaust("This")),
    ]
