from . import *


def GetAbilities() -> Sequence['Ability']:
    def maggia_count(effect: 'Effect', ui: List['CardFace']) -> int:
        enemies = Worlds.FindCardsOnField(effect, card_type=Enemy, trait="MAGGIA")
        ui.extend(enemies)
        return len(enemies)

    return [
        AbilityFactory.ThisGainKeyword(
            maggia_count,
            scheme=1,
            change_on_event=OnEvent.CardInPlay(Enemy),
        ),
    ]
