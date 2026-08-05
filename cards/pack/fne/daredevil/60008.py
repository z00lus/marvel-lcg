from . import *

# Cross-Examination


def GetAbilities() -> Sequence['Ability']:

    def cross_examination(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        this = effect.this.CastTo(Event)
        target = effect.targets[0]
        upgrades = GetAttachedUpgradeCount(target)
        additional = effect.GetInitiator().AskChooseOneText(
            list(range(upgrades + 1)),
            [f"Deal {value} additional damage" for value in range(upgrades + 1)],
        )
        this.DealDamage([target], 3 + additional, effect)

    return [
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.HeroAction,
            cross_examination,
        ).SetPlay().SetLabel("attack").SetTarget(Enemy),
    ]
