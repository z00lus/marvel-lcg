from cards.pack import *


def FindBullseye(effect: 'Effect', player: 'Player') -> 'Minion|None':
    return Search.EncounterCard(
        effect,
        player,
        include_discard_pile=True,
        include_set_aside=True,
        name="Bullseye",
        card_type=Minion,
    )


def BullseyeInPlay(effect: 'Effect') -> 'Minion|None':
    face = Worlds.FindCardOnField(effect, name="Bullseye", card_type=Minion)
    return face.CastTo(Minion) if face else None
