from . import *

# Avengers Compound


def GetAbilities() -> Sequence['Ability']:

    def tuck_ally(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        effect.this.CastTo(Support).TuckCardUnderHere(effect.targets, effect, peek=True)

    def play_ally(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        this = effect.this.CastTo(Support)
        effect.GetInitiator().PlayCardsLikeInTurn(
            this.GetPlacedCardArea().GetAll(),
            effect,
            if_not_play_discard_it=False,
        )

    def can_play_tucked_ally(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> bool:
        tucked = effect.this.GetPlacedCardArea().GetAll()
        return len(tucked) == 1 and tucked[0].CanPlayBy(effect.GetInitiator())

    return [
        AbilityFactory.CanPlayThisSupportCard().SetPlay(
            only_if_your_identity_has_trait="AVENGER"
        ),
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.Action,
            tuck_ally,
            conditions=[
                lambda effect, message: effect.this.GetPlacedCardArea().GetSize() == 0,
            ],
        ).SetCostFunc(CostFunc.Exhaust("This"))
        .SetTarget("YourHandCards", card_type=Ally),
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.Action,
            play_ally,
            conditions=[
                can_play_tucked_ally,
            ],
        ).SetCostFunc(CostFunc.Exhaust("This")),
    ]
