from . import *


def GetAbilities() -> Sequence['Ability']:

    def cap_damage(effect: 'Effect', message: 'Message.WhenUnitWouldTakeDamage') -> None:
        this = effect.this.CastTo(Attachment)
        prevented = max(0, message.will_take_damage - 3)
        if prevented == 0:
            return
        message.PreventDamage(prevented, effect)
        Faces.PlaceCountersOn([this], prevented, 'damage', effect)
        if this.GetCounters('damage') >= 6:
            this.card.Flip(effect)

    return [
        AbilityFactory.AttachToFaceWhenPutIntoPlay(BULLSEYE),
        AbilityFactory.WhenUnitWouldTakeDamage(
            AbilityType.ForcedInterrupt,
            BULLSEYE,
            cap_damage,
        ),
    ]
