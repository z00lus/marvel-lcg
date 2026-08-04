from . import *

# * Echo's Katana


def GetAbilities() -> Sequence['Ability']:

    def echos_katana(effect: 'Effect', message: 'Message.AfterPlayerPlayedCard') -> None:
        this = effect.this.CastTo(Upgrade)
        value = FacesCounter.GetPrintedCost([message.played_face])
        this.DealDamage(
            effect.targets,
            value,
            effect,
            property=AttackProperty(piercing=True),
        )

    return [
        AbilityFactory.AfterPlayerPlayedCard(
            AbilityType.HeroResponse,
            "You",
            Event,
            echos_katana,
        ).SetCostFunc(CostFunc.Exhaust("This"))
        .SetTarget(Enemy),
    ]
