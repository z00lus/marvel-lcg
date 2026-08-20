from . import *


def GetAbilities() -> Sequence['Ability']:
    martial_artist = CardFinder(
        name="Kingpin",
        card_type=Villain,
        check_effect_fn=lambda effect, face: face.HasTrait("MARTIAL ARTIST"),
    )

    def absorb(effect: 'Effect', message: 'Message.WhenUnitWouldTakeDamage') -> None:
        this = effect.this.CastTo(Attachment)
        message.SetBeInstead(effect)
        Faces.PlaceCountersOn([this], message.will_take_damage, 'damage', effect)
        if this.GetCounters('damage') >= 8:
            Faces.DiscardAll([this], effect)

    return [
        AbilityFactory.AttachToFaceWhenPutIntoPlay(
            martial_artist,
            if_cannot_gain_surge=True,
        ),
        *AbilityFactory.GiveKeywordToAttached(Villain, retaliate=1),
        AbilityFactory.WhenUnitWouldTakeDamage(
            AbilityType.ForcedInterrupt,
            "AttachedEnemy",
            absorb,
        ),
    ]
