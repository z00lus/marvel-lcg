from . import *


def GetAbilities() -> Sequence['Ability']:
    def highest_thwart(effect: 'Effect', ui: List['CardFace']) -> int:
        characters = Worlds.FindCardsOnField(effect, card_type=Friend)
        values = [character.thwart for character in characters if HasThwart.IsType(character)]
        return max(values, default=0)

    def revealed(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        effect.this.CastTo(Minion).DoSchemes(message.GetToPlayer(), effect)

    return [
        AbilityFactory.ThisGainKeyword(
            highest_thwart,
            scheme=1,
            change_on_event=OnEvent.CardInPlay(Friend),
        ),
        AbilityFactory.WhenThisRevealed(None, revealed),
    ]
