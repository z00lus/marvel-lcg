from . import *


def GetAbilities() -> Sequence['Ability']:

    def cold_as_ice(effect: 'Effect', message: 'Message.AfterUnitSchemeEnd') -> None:
        first_player = Worlds.GetFirstPlayer(effect)
        Faces.GiveStatus([first_player.GetIdentity()], "Confused", effect)
        Faces.DiscardAll([effect.this], effect)

    return [
        AttachToHighestHpMinionAndGiveTough(),
        AbilityFactory.AfterUnitSchemeEnd(
            AbilityType.ForcedResponse,
            "AttachedMinion",
            cold_as_ice,
        ),
    ]
