from . import *


def GetAbilities() -> Sequence['Ability']:

    def piecing_it_all_together(effect: 'Effect', message: 'Message.WhenSchemeBeDefeated') -> None:
        player = message.GetDefeatingPlayer()
        player.DrawUp(3, effect)

    return [
        AbilityFactory.WhenSchemeBeDefeated(
            AbilityType.WhenDefeated,
            "This",
            piecing_it_all_together,
            has_defeating_player=True,
        ),
    ]
