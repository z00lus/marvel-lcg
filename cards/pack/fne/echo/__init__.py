from cards.pack import *


def IsAspectOrBasicEvent(face: 'CardFace') -> bool:
    return Event.IsType(face) and (face.IsClass("Basic") or face.GetAspect() is not None)


def FindKingpin(effect: 'Effect', player: 'Player') -> 'Minion|None':
    face = Search.EncounterCard(
        effect,
        player,
        include_discard_pile=True,
        include_set_aside=True,
        name="Kingpin",
        card_type=Minion,
    )
    return face


def PutKingpinIntoPlay(effect: 'Effect', player: 'Player') -> 'Minion|None':
    kingpin = FindKingpin(effect, player)
    if kingpin:
        kingpin.PutIntoPlay(player, effect)
    return kingpin
