from . import *


def GetAbilities() -> Sequence['Ability']:
    def attack(effect: 'Effect', message: 'Message.WhenUnitWouldAttack') -> None:
        message.GiveAdditionalBoostCardForThisActivation(1, effect)
        message.GainOverKill(effect)

    def discharge(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        Unused(effect, message)

    return [
        AbilityFactory.AttachToFaceWhenPutIntoPlay(ELECTRO),
        AbilityFactory.WhenUnitAttackYou(
            AbilityType.ForcedInterrupt,
            ELECTRO,
            attack,
        ).SetCostFunc(CostFunc.Counter("This", 1, 'charge')),
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.HeroAction,
            discharge,
        ).SetName("Discharge Electric Charge")
        .SetCost(Cost("Y", or_cost=Cost("2")))
        .SetCostFunc(CostFunc.Counter("This", 1, 'charge')),
    ]
