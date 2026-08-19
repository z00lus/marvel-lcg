from cards.pack import *


DAILY_BUGLE_SUPPORT = CardFinder(
    card_type=Support,
    trait="DAILY BUGLE",
)
STAMINA = "stamina"


def GetDailyBugleSupports(effect: 'Effect') -> List['Support']:
    return effect.world.FindCardsOnField(
        card_type=Support,
        trait="DAILY BUGLE",
    )


def GetControlledDailyBugleSupports(
    effect: 'Effect',
    player: 'Player',
    *,
    ready: bool|None=None,
    with_stamina: bool=False,
) -> List['Support']:
    supports = [
        support for support in GetDailyBugleSupports(effect)
        if support.GetControlByPlayer() == player
    ]
    if ready is not None:
        supports = [support for support in supports if support.IsReady() == ready]
    if with_stamina:
        supports = [support for support in supports if support.GetCounters(STAMINA) > 0]
    return supports


def RemoveStamina(support: 'Support', effect: 'Effect') -> None:
    support.RemoveCountersInternal(1, STAMINA, effect, forced=False)
