from . import *


def GetAbilities() -> Sequence['Ability']:
    def revealed(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        minion = Filter.One(
            Worlds.GetOnFieldMinions(effect),
            effect,
            fewest_remaining_hp=True,
        )
        if minion:
            Faces.DefeatUnits([minion], effect.this, effect)
        revealed_minion = Worlds.DiscardEncounterCardsUntil(effect, card_type=Minion)
        if revealed_minion:
            revealed_minion.Reveal(message.GetToPlayer(), effect)

    return [AbilityFactory.WhenThisRevealed(None, revealed)]
