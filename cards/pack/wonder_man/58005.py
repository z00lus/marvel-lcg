from . import *

# Starstruck


def GetAbilities() -> Sequence['Ability']:

    def starstruck(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        this = effect.this.CastTo(Event)
        value = effect.GetInitiator().GetHero().attack
        this.AttackDamage(effect.targets, value, effect)
        if EnergyOverpaid(effect, 1):
            Faces.GiveStatus(effect.targets, "Stunned", effect)

    return [
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.HeroAction,
            starstruck,
        ).SetPlay().SetLabel('attack').SetTarget(Enemy),
    ]
