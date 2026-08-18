from . import *


def GetAbilities() -> Sequence['Ability']:

    def after_scheme(effect: 'Effect', message: 'Message.AfterUnitSchemeEnd') -> None:
        this = effect.this.CastTo(Attachment)
        Faces.RemoveCountersOn([this], 3, 'damage', effect)
        if this.GetCounters('damage') == 0:
            this.card.Flip(effect)

    def boost(effect: 'Effect', message: 'Message.WhenCardBecomeBoost') -> None:
        this = effect.this.CastTo(Attachment)
        Faces.PlaceCountersOn([this], 1, 'damage', effect)

    return [
        AbilityFactory.AttachToFaceWhenPutIntoPlay(BULLSEYE),
        AbilityFactory.AfterUnitSchemeEnd(
            AbilityType.ForcedResponse,
            BULLSEYE,
            after_scheme,
        ),
        AbilityFactory.WhenCardBecomeBoost("This", boost),
    ]
