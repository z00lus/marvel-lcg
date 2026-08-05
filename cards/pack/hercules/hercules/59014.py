from . import *


def GetAbilities() -> Sequence['Ability']:

    def golden_mace(effect: 'Effect', message: 'Message.WhenUnitWouldAttack') -> None:
        message.GainATKForThisAttack(CountGifts(effect.GetInitiator()), effect)
        message.GainOverKill(effect)

    return [
        AbilityFactory.WhenUnitMakeAttack(
            AbilityType.HeroInterrupt,
            CardFinder(name="Hercules", card_type=Hero),
            golden_mace,
            is_basic_attack=True,
        ).SetCostFunc(CostFunc.Exhaust("This")),
    ]
