from . import *


def GetAbilities() -> Sequence['Ability']:

    def wisdom_of_athena(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        effect.this.CastTo(Event).RemoveThreatFromSchemes(effect.targets, 4, effect)

    return [
        AbilityFactory.ReduceCostToPlayThis(
            lambda effect: CountGifts(effect.GetInitiator()),
        ),
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.HeroAction,
            wisdom_of_athena,
        ).SetPlay().SetLabel("thwart").SetTarget(Scheme2),
    ]
