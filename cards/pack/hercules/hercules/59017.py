from . import *


def GetAbilities() -> Sequence['Ability']:

    def prince_of_power(effect: 'Effect', message: 'Message.AfterUnitDefeatedUnit') -> None:
        identity = effect.GetInitiator().GetIdentity()
        identity.Heal(message.excess_damage, effect)

    return [
        AbilityFactory.AfterUnitAttackAndDefeatUnit(
            AbilityType.HeroResponse,
            CardFinder(name="Hercules", card_type=Hero),
            Enemy,
            prince_of_power,
            has_excess_damage=True,
        ).SetCostFunc(CostFunc.Exhaust("This")),
    ]
