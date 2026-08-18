from . import *


def GetAbilities() -> Sequence['Ability']:

    def scheme(effect: 'Effect', message: 'Message.WhenUnitWouldScheme') -> None:
        this = effect.this.CastTo(Minion)
        villain = Worlds.FindVillain(effect)
        message.SetBeInstead(effect)
        if villain:
            this.BasicAttack([villain], effect)

    def defeated(effect: 'Effect', message: 'Message.AfterUnitBeDefeated') -> None:
        scheme = Worlds.FindMainScheme(effect)
        if scheme:
            scheme.PlaceThreatOnSchemes([scheme], 2, effect)

    return [
        AbilityFactory.WhenUnitWouldScheme(
            AbilityType.ForcedInterrupt,
            "This",
            scheme,
        ),
        AbilityFactory.AfterUnitBeDefeated(
            AbilityType.WhenDefeated,
            "This",
            defeated,
        ),
    ]
