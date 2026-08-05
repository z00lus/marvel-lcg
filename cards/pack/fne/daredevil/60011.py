from . import *

# Raising Hell


def GetAbilities() -> Sequence['Ability']:

    def raising_hell(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        this = effect.this.CastTo(Event)
        damage_per_upgrade = 3 if effect.GetInitiator().GetHero().HasTrait("AERIAL") else 2
        for enemy in Worlds.GetOnFieldEnemies(effect):
            damage = damage_per_upgrade * GetAttachedUpgradeCount(enemy)
            if damage:
                this.DealDamage([enemy], damage, effect)

    return [
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.HeroAction,
            raising_hell,
        ).SetPlay().SetLabel("attack"),
    ]
