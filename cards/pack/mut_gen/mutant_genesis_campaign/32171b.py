from . import *


# Metro P.D.

def GetAbilities() -> Sequence['Ability']:
    def metro_pd(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        player = effect.GetInitiator()
        player.ChooseAbilities(
            effect,
            AbilityFactory.ForChoiceAbility(
                "Deal 1 damage to an enemy",
                lambda targets: effect.this.DealDamage(targets, 1, effect),
            ).SetTarget(Enemy),
            AbilityFactory.ForChoiceAbility(
                "Remove 1 threat from a scheme",
                lambda targets: effect.this.RemoveThreatFromSchemes(targets, 1, effect),
            ).SetTarget(Scheme2),
        )

    return [
        AbilityFactory.FirstPlayerControlThis(),
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.Action,
            metro_pd,
        ).SetCostFunc(CostFunc.Exhaust("This")),
    ]
