from . import *


def GetAbilities() -> Sequence['Ability']:
    def find_the_norn_stones(
        effect: 'Effect',
        message: 'Message.WhenSchemeBeDefeated',
    ) -> None:
        this = effect.this.CastTo(EncounterSideScheme)
        for player in Worlds.GetPlayers(effect):
            stone = CardFactory.GenerateCard(
                "21187a,21187b",
                None,
                effect.world,
            ).face
            stone.PutIntoPlay(player, effect, under_control=True)
        this.card.Flip(effect)

    return [
        AbilityFactory.ThreatCannotBeRemovedFromWhile(
            "This",
            while_face_is_in_play=CardFinder(
                name="Hela",
                card_type=Villain,
                trait="MYSTIC",
            ),
        ),
        AbilityFactory.WhenSchemeBeDefeated(
            AbilityType.WhenDefeated,
            "This",
            find_the_norn_stones,
        ),
    ]
