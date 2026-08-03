from . import *


def GetAbilities() -> Sequence['Ability']:
    def norn_stone(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        Faces.ReadyAll(effect.targets, effect)
        effect.this.card.Flip(effect)

    return [
        *AbilityFactory.GiveKeywordToAttached(
            Hero,
            thwart=1,
            attack=1,
            defense=1,
        ),
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.HeroAction,
            norn_stone,
        ).SetTarget("YourHero", canbe_ready=True),
    ]
