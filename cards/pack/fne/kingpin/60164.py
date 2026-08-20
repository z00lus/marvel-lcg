from . import *


def GetAbilities() -> Sequence['Ability']:
    kingpin_is_martial_artist = lambda effect, face: (
        face == Select.GetYou(effect).GetHero()
        and (villain := Worlds.FindVillain(effect)) is not None
        and villain.HasTrait("MARTIAL ARTIST")
    )

    def spend_grip(effect: 'Effect', message: 'Message.WhenUnitWouldAttack|Message.WhenUnitWouldThwart') -> None:
        message.SetBeInstead(effect)
        Faces.RemoveCountersOn([effect.this], 1, 'grip', effect)

    return [
        AbilityFactory.AttachToFaceWhenPutIntoPlay(
            CardFinder(card_type=Hero, check_effect_fn=kingpin_is_martial_artist),
            if_cannot_gain_surge=True,
        ),
        AbilityFactory.PlayersCannotChangeForms(
            AbilityType.NonKeyword,
            "AttachedPlayer",
            from_form=Hero,
            to_form=AlterEgo,
        ),
        AbilityFactory.WhenUnitWouldAttackOrThwart(
            AbilityType.ForcedInterrupt,
            "AttachedCharacter",
            spend_grip,
        ),
    ]
