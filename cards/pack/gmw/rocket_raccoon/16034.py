from . import *

# Battery Pack

def GetAbilities() -> Sequence['Ability']:

    def battery_pack(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        this = effect.this.CastTo(Upgrade)
        upgrade = effect.targets[0].CastTo(Upgrade)
        Faces.MoveCounters(this, upgrade, 1, 'all-purpose', effect)


    return [
        AbilityFactory.ThisEnterPlayWithCounters(2, "charge"),
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.Action,
            battery_pack,
            conditions=[
                lambda effect, message:
                    effect.this.CastTo(Upgrade).GetCounters('charge') > 0,
            ],
        ).SetCostFunc(CostFunc.Exhaust("This"))
        .SetTarget(Upgrade, trait="TECH", another=True, from_where=["YouControlCards"])
    ]
