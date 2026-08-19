from cards.pack import *


def FindTracksuitMafia(effect: 'Effect') -> 'EncounterSideScheme|None':
    return Worlds.FindCardOnField(
        effect,
        name="Tracksuit Mafia",
        card_type=EncounterSideScheme,
    )


def TuckUnderTracksuitMafia(effect: 'Effect', minion: 'Minion') -> bool:
    scheme = FindTracksuitMafia(effect)
    if not scheme:
        return False
    scheme.PlaceCardHere(minion, False, effect)
    return True
