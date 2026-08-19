from . import *


def GetAbilities() -> Sequence['Ability']:
    def defeated(effect: 'Effect', message: 'Message.WhenUnitBeDefeated') -> None:
        this = effect.this.CastTo(Minion)
        if TuckUnderTracksuitMafia(effect, this):
            return
        if Unit2.IsType(message.killer):
            Faces.GiveStatus([message.killer], "Stunned", effect)
            Faces.GiveStatus([message.killer], "Confused", effect)

    return [
        AbilityFactory.WhenUnitBeDefeated(
            AbilityType.WhenDefeated,
            "This",
            defeated,
        ),
    ]
