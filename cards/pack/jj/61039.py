from . import *


def GetAbilities() -> Sequence['Ability']:

    def lay_low(effect: 'Effect', message: 'Message.WhenSchemeBeDefeated') -> None:
        Players.ForEachPlayer(effect, lambda player: YouMayFlipToYourAlterEgoForm(player, effect))
        for alter_ego in Worlds.GetOnFieldAlterEgos(effect):
            effect.this.HealthUnits([alter_ego], alter_ego.recover, effect)

    return [
        AbilityFactory.WhenSchemeBeDefeated(
            AbilityType.WhenDefeated,
            "This",
            lay_low,
        ),
    ]
