from . import *


def GetAbilities() -> Sequence['Ability']:
    def hinder(effect: 'Effect', message: 'Message.AfterCardEnterPlay') -> None:
        if Worlds.IsExpert(effect):
            effect.this.CastTo(EncounterSideScheme).PlaceThreatInternal("3*", effect)

    def defeated(effect: 'Effect', message: 'Message.WhenSchemeBeDefeated') -> None:
        psyche = Worlds.FindCardOnField(effect, DISTURBED_PSYCHE)
        if psyche:
            Faces.PlaceCountersOn([psyche], 1, 'threat', effect)
        effect.this.card.Flip(effect, call_reveal=False)
        walker = effect.this.card.face
        villain = Worlds.FindVillain(effect)
        if villain and Attachment.IsType(walker):
            walker.AttachTo2(villain, effect)

    return [
        AbilityFactory.AfterCardEnterPlay(
            AbilityType.ForcedResponse,
            "This",
            hinder,
        ),
        AbilityFactory.WhenSchemeBeDefeated(
            AbilityType.ForcedResponse,
            "This",
            defeated,
        ),
    ]
