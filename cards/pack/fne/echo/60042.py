from . import *

# * The Rez


def GetAbilities() -> Sequence['Ability']:

    def the_rez(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        this = effect.this.CastTo(Support)
        Unused(this)

        identity = effect.GetInitiator().GetIdentity()
        costs = [FacesCounter.GetPrintedCost([face]) for face in identity.GetPlacedCardArea().GetAll()]
        value = max(costs, default=0)
        identity.HealthUnits([identity], value, effect)

    return [
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.AlterEgoAction,
            the_rez,
        ).SetCostFunc(CostFunc.Exhaust("This")),
    ]
