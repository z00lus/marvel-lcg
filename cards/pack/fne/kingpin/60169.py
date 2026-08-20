from . import *


def GetAbilities() -> Sequence['Ability']:
    def place_threat(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        this = effect.this.CastTo(Minion)
        Faces.PlaceCountersOn([this], 1, 'threat', effect)
        if this.GetCounters('threat') >= 4:
            Faces.TreatAsAlly(this, "karma_controlled_ally", message.GetToPlayer(), effect)

    return [
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.HeroAction,
            place_threat,
            conditions=[lambda effect, message: effect.this.GetCounters('threat') < 4],
        ).SetCostFunc(CostFunc.Spend(Cost("B"))),
    ]
