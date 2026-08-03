from . import *


def GetAbilities() -> Sequence['Ability']:
    def defensive_protocols(
        effect: 'Effect',
        message: 'Message.WhenPlayerPhaseEnd',
    ) -> None:
        this = effect.this.CastTo(EncounterSideScheme)
        Faces.PlaceCountersOn([this], 1, "crash", effect)
        if this.GetCounters("crash") < 2:
            return

        for player in Worlds.GetPlayers(effect):
            CardFactory.GenerateCard("21185", player.hand_cards, effect.world)
        Faces.RemoveAllFromGame([this], effect)

    return [
        AbilityFactory.WhenPlayerPhaseEnd(
            AbilityType.ForcedInterrupt,
            defensive_protocols,
        ),
    ]
