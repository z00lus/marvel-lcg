from . import *


def GetAbilities() -> Sequence['Ability']:
    def revealed(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        support = Worlds.GetSetAsideAreaCards(effect, PUBLIC_SUPPORT)
        if support:
            support[0].PutIntoPlay("FirstPlayer", effect)

    def call_for_backup(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        discard = Worlds.GetEncounterDiscardPileCards(effect)
        if discard:
            Faces.ShuffleAllTo(discard, "EncounterDeck", effect)
        minion = Worlds.DiscardEncounterCardsUntil(effect, card_type=Minion)
        if minion:
            minion.Reveal(message.GetToPlayer(), effect)

    required = lambda effect: 4 if Worlds.IsExpert(effect) else 5
    standard = AbilityFactory.WhenInYourPlayTurn(
        AbilityType.HeroAction,
        call_for_backup,
        conditions=[
            lambda effect, message: not Worlds.IsExpert(effect),
            lambda effect, message: effect.this.threat >= required(effect),
        ],
    ).SetCostFunc(CostFunc.RemoveThreatFrom("This", 5, ignore_crisis=True))
    expert = AbilityFactory.WhenInYourPlayTurn(
        AbilityType.HeroAction,
        call_for_backup,
        conditions=[
            lambda effect, message: Worlds.IsExpert(effect),
            lambda effect, message: effect.this.threat >= required(effect),
        ],
    ).SetCostFunc(CostFunc.RemoveThreatFrom("This", 4, ignore_crisis=True))

    return [
        AbilityFactory.WhenThisRevealed(None, revealed),
        standard,
        expert,
    ]
