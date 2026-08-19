from . import *


def GetAbilities() -> Sequence['Ability']:

    def prisoner_defeated(effect: 'Effect', message: 'Message.WhenUnitBeDefeated') -> None:
        this = effect.this.CastTo(MainScheme)
        prisoner = message.trigger.CastTo(Minion)
        value = 2 if prisoner.HasTrait("ELITE") else 1
        this.RemoveThreatFromSchemes(
            [this],
            value,
            effect,
            ignore_crisis=True,
        )

    return [
        AbilityFactory.WhenUnitBeDefeated(
            AbilityType.WhenDefeated,
            CardFinder2("PRISONER", Minion),
            prisoner_defeated,
        ),
    ]
