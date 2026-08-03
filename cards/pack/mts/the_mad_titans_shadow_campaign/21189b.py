from . import *


def GetAbilities() -> Sequence['Ability']:
    def jormungand(
        effect: 'Effect',
        message: 'Message.WhenUnitBeDefeated',
    ) -> None:
        Faces.RemoveAllFromGame([effect.this], effect)

    return [
        *AbilityFactory.GiveKeywordToAttached(
            Villain,
            health=lambda effect: 4 * len(Worlds.GetPlayers(effect)),
        ),
        AbilityFactory.WhenUnitBeDefeated(
            AbilityType.ForcedInterrupt,
            "AttachedVillain",
            jormungand,
        ),
    ]
