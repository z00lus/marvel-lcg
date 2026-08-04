from . import *

# Study the Tape


def GetAbilities() -> Sequence['Ability']:

    def study_the_tape(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        this = effect.this.CastTo(Event)
        Unused(this)

        initiator = effect.GetInitiator()
        face = Search.PlayerCard(
            effect,
            initiator,
            include_player_deck=False,
            include_discard_pile=True,
            finder=CardFinder(
                check_face_fn=lambda face:
                    IsAspectOrBasicEvent(face) or face.IsName("Photographic Reflexes")
            ),
        )
        if face:
            Faces.AddToHand([face], initiator, effect)

    return [
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.Action,
            study_the_tape,
        ).SetPlay().SetLabel(),
    ]
