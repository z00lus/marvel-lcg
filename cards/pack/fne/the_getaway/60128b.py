from . import *


def GetAbilities() -> Sequence['Ability']:

    def end_round(effect: 'Effect', message: 'Message.WhenRoundEnd') -> None:
        this = effect.this.CastTo(MainScheme)
        if this.threat == 0:
            return
        Faces.PlaceCountersOn([this], 1, 'speed', effect)
        alongside = Worlds.FindCardOnField(
            effect,
            name="Alongside",
            card_type=Attachment,
        )
        if alongside:
            alongside.card.Flip(effect)
        else:
            Faces.PlaceCountersOn([this], 1, 'speed', effect)

    return [
        AbilityFactory.WhenRoundEnd(
            AbilityType.ForcedInterrupt,
            None,
            end_round,
        ),
    ]
