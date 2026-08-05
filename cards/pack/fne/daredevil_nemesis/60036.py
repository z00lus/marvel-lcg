from . import *

# Eye on the Target


def GetAbilities() -> Sequence['Ability']:

    def eye_on_the_target(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        this = effect.this.CastTo(Treachery)
        player = message.GetToPlayer()
        bullseye = BullseyeInPlay(effect)
        removable = player.GetControlCards(
            CardFinder(card_type=Ally|Support, check_face_fn=lambda face:
                Ally.IsType(face) or face.HasTrait("PERSONA"))
        )

        choices = []
        if removable:
            choices.append(
                AbilityFactory.ForChoiceAbility(
                    "Remove an ally or Persona support you control from the game",
                    lambda targets: Faces.RemoveAllFromGame(targets, effect),
                ).SetTarget(
                    CardFinder(card_type=Ally|Support, check_face_fn=lambda face:
                        Ally.IsType(face) or face.HasTrait("PERSONA")),
                    from_where=["YouControlCards"],
                )
            )
        if bullseye:
            choices.append(
                AbilityFactory.ForChoiceAbility(
                    "Bullseye attacks you",
                    lambda targets: bullseye.DoAttackYou(player, effect),
                )
            )
        if choices:
            player.ChooseAbilities(effect, *choices)

        if not BullseyeInPlay(effect):
            found = FindBullseye(effect, player)
            if found:
                found.Reveal(player, effect)

    return [
        AbilityFactory.WhenThisRevealed(
            None,
            eye_on_the_target,
        ),
    ]
