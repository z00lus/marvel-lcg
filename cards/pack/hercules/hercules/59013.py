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

    def has_gift(effect: 'Effect', message: 'Message.WhenUnitWouldDefend') -> bool:
        return CountGifts(effect.GetInitiator()) > 0

    return [
        AbilityFactory.WhenUnitDefendAgainstAttack(
            AbilityType.HeroInterrupt,
            CardFinder(name="Hercules", card_type=Hero),
            gauntlets,
            conditions=[has_gift],
        ).SetCostFunc(CostFunc.Exhaust("This")),
    ]
