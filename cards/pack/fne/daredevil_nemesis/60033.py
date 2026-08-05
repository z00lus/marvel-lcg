from . import *

# * Bullseye


def GetAbilities() -> Sequence['Ability']:

    def bullseye(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        this = effect.this.CastTo(Minion)
        player = message.GetToPlayer()
        personas = player.GetControlCards(CardFinder(card_type=Support, trait="PERSONA"))
        player.ChooseAbilities(
            effect,
            AbilityFactory.ForChoiceAbility(
                "Discard a Persona support you control",
                lambda targets: Faces.DiscardAll(targets, effect),
                condition=bool(personas),
            ).SetTarget(
                CardFinder(card_type=Support, trait="PERSONA"),
                from_where=["YouControlCards"],
            ),
            AbilityFactory.ForChoiceAbility(
                "Bullseye attacks you",
                lambda targets: this.DoAttackYou(player, effect),
            ),
        )

    return [
        AbilityFactory.WhenThisRevealed(
            None,
            bullseye,
        ),
    ]
