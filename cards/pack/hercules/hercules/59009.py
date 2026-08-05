from . import *


def GetAbilities() -> Sequence['Ability']:

    def gift_of_battle(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        effect.this.CastTo(Event).DealDamage(
            effect.targets,
            5,
            effect,
            property=AttackProperty(),
        )

    return [
        AbilityFactory.ReduceCostToPlayThis(
            lambda effect: CountGifts(effect.GetInitiator()),
        ),
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.HeroAction,
            gift_of_battle,
        ).SetPlay().SetLabel("attack").SetTarget(Enemy),
    ]
