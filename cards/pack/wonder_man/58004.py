from . import *

# Ionic Blast


def GetAbilities() -> Sequence['Ability']:

    def ionic_blast(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        value = 3 + 2 * EnergyOverpaid(effect, 3)
        effect.this.CastTo(Event).AttackDamage(effect.targets, value, effect)

    return [
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.HeroAction,
            ionic_blast,
        ).SetPlay().SetLabel('attack').SetTarget(Enemy),
    ]
