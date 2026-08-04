from . import *

# * Maya Lopez


def GetAbilities() -> Sequence['Ability']:

    def practice_makes_perfect(effect: 'Effect', message: 'Message.WhenUnitWouldChangeForm') -> None:
        this = effect.this.CastTo(AlterEgo)
        Unused(this)

        initiator = effect.GetInitiator()
        face = Search.PlayerCard(
            effect,
            initiator,
            include_player_deck=True,
            finder=CardFinder(check_face_fn=IsAspectOrBasicEvent),
        )
        if face:
            Faces.AddToHand([face], initiator, effect)

    return [
        AbilityFactory.WhenUnitWouldChangeForm(
            AbilityType.Interrupt,
            "You",
            practice_makes_perfect,
            to_form=Hero,
        ).SetName("Practice Makes Perfect"),
    ]
