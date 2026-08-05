from . import *

# Dance with the Devil


def GetAbilities() -> Sequence['Ability']:

    def dance_with_the_devil(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        this = effect.this.CastTo(Upgrade)
        enemy = this.GetBindFace().CastTo(Enemy)
        Faces.DiscardAll([this], effect)
        this.DealDamage([enemy], 3, effect)

    return [
        AbilityFactory.CanPlayThisUpgradeCard(Enemy).SetTarget2("TeamUp", is_optional=False),
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.HeroAction,
            dance_with_the_devil,
        ).SetLabel("attack"),
    ]
