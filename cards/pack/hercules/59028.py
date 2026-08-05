from . import *


def GetAbilities() -> Sequence['Ability']:

    def evaluate_threat(effect: 'Effect', message: 'Message.WhenSchemeBeDefeated') -> None:
        finder = CardFinder(trait="AVENGER") | CardFinder(trait="S.H.I.E.L.D")

        def search_for_player(player: 'Player') -> None:
            face = Search.PlayerCard(
                effect,
                player,
                include_player_deck=True,
                include_discard_pile=True,
                finder=finder,
                may=True,
            )
            if face:
                Faces.MoveAllTo([face], player.hand_cards, effect)
                Worlds.UpdateNextCardPlayCost(
                    player,
                    -2,
                    effect,
                    finder=CardFinder(check_face_fn=lambda candidate, chosen=face: candidate == chosen),
                    in_this="Phase",
                )

        Players.ForEachPlayer(effect, search_for_player)

    return [
        AbilityFactory.CanPlayThisSchemeCard(
            conditions=[
                lambda effect, message:
                    effect.GetInitiator().GetIdentity().HasTrait("AVENGER", "S.H.I.E.L.D"),
            ],
        ),
        AbilityFactory.WhenSchemeBeDefeated(
            AbilityType.WhenDefeated,
            "This",
            evaluate_threat,
        ),
    ]
