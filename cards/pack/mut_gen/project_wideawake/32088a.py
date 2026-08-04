from . import *

# Mutants at the Mall

def GetAbilities() -> Sequence['Ability']:

    def mutants_at_the_mall(effect: 'Effect', message: 'Message.WhenSchemeBeDefeated') -> None:
        this = effect.this.CastTo(EncounterSideScheme)
        Unused(this)

        player = Worlds.GetFirstPlayer(effect)
        minion = Search.EncounterCard(
            effect,
            player,
            include_discard_pile=True,
            trait="SENTINEL",
            card_type=Minion
        )

        if minion:
            minion.Reveal(player, effect)

        # discarding any other version of Jubilee from play.
        faces = Worlds.FindCardsOnField(
            effect,
            name="Jubilee",
            card_type=Ally
        )
        Faces.DiscardAll(faces, effect)

        this.card.Flip(effect)
        this.card.face.PutIntoPlay(player, effect, under_control=True)


    return [
        AbilityFactory.WhenSchemeBeDefeated(
            AbilityType.WhenDefeated,
            "This",
            mutants_at_the_mall,
        ),
    ]
