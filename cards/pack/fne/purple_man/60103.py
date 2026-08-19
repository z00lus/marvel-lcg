from . import *


def GetAbilities() -> Sequence['Ability']:
    def defeated(effect: 'Effect', message: 'Message.WhenUnitBeDefeated') -> None:
        ally = Filter.One(
            Worlds.GetOnFieldAllies(effect),
            effect,
            highest_atk=True,
        )
        if ally:
            Faces.DiscardAll([ally], effect)

    return [
        AbilityFactory.WhenUnitBeDefeated(
            AbilityType.WhenDefeated,
            "This",
            defeated,
        ),
        PurpleManBoostAbility(),
    ]
