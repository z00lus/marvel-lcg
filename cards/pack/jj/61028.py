from . import *


def GetAbilities() -> Sequence['Ability']:

    def second_chance(effect: 'Effect', message: 'Message.WhenSchemeBeDefeated') -> None:
        def action(player: 'Player') -> None:
            identity_set = player.GetIdentity().paper.set_name
            cards = [
                face for face in player.discard_pile.GetAll()
                if face.paper.set_name == identity_set
            ]
            if cards:
                player.MayChooseOneAbility(
                    effect,
                    AbilityFactory.ForChoiceAbility(
                        "Shuffle all identity-specific cards from your discard pile into your deck",
                        lambda targets: Faces.ShuffleAllTo(cards, player.player_deck, effect),
                    ),
                )

        Players.ForEachPlayer(effect, action)

    return [
        AbilityFactory.WhenSchemeBeDefeated(
            AbilityType.WhenDefeated,
            "This",
            second_chance,
        ),
    ]
