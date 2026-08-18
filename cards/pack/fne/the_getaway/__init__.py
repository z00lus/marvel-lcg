from cards.pack import *


GETAWAY = CardFinder(name="The Getaway", card_type=MainScheme)


def GetGetaway(effect: 'Effect') -> 'MainScheme|None':
    return Worlds.FindCardOnField(effect, GETAWAY)


def GetSpeed(effect: 'Effect') -> int:
    scheme = GetGetaway(effect)
    return scheme.GetCounters('speed') if scheme else 0
