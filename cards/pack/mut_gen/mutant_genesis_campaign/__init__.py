from cards.pack import *


def ShuffleRandomFuturePastCardIntoEncounterDeck(effect: 'Effect') -> None:
    faces = Worlds.AsideDeck(effect).FindCards(set_name="Future Past")
    if faces:
        face = Rand.RandomChoice(faces, effect)
        Faces.ShuffleAllTo([face], "EncounterDeck", effect)
