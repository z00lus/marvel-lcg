from . import *


def GetAbilities() -> Sequence['Ability']:
    def armor(effect: 'Effect', message: 'Message.WhenUnitWouldTakeDamage') -> None:
        this = effect.this.CastTo(Attachment)
        message.SetBeInstead(effect)
        Faces.PlaceCountersOn([this], message.will_take_damage, 'damage', effect)
        limit = 8 if Worlds.IsExpert(effect) else 5
        if this.GetCounters('damage') >= limit:
            Faces.DiscardAll([this], effect)

    def boost(effect: 'Effect', message: 'Message.WhenCardBecomeBoost') -> None:
        if IsActivatingMary(message, "Bloody Mary"):
            Faces.GiveStatus([message.GetToPlayer().GetIdentity()], "Confused", effect)

    return [
        AbilityFactory.AttachToFaceWhenPutIntoPlay(Villain),
        AbilityFactory.WhenUnitWouldTakeDamage(
            AbilityType.ForcedInterrupt,
            "AttachedEnemy",
            armor,
        ),
        AbilityFactory.WhenCardBecomeBoost("This", boost),
    ]
