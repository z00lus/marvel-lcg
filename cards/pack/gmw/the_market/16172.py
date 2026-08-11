from . import *

# Navigation Column

def GetAbilities() -> Sequence['Ability']:

    def navigation_column(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        this = effect.this.CastTo(Upgrade)
        Unused(this)

        initiator = effect.GetInitiator()
        initiator.DrawUp(1, effect)

    def navigation_column_cost(targets: Sequence['CardFace'], effect: 'Effect') -> bool:
        initiator = effect.GetInitiator()

        if initiator.IsControl(CardFinder(name="Milano")):
            initiator.DiscardDeckTopCards(1, effect)
            return True
        else:
            return initiator.DiscardHandCards((1, 1), effect) != []

    return [
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.HeroAction,
            navigation_column
        # Ask for and commit the discard first. If the player cancels the hand
        # choice, the deterministic exhaust cost has not been paid yet.
        ).SetCostFunc(CostFunc.Custom(None, navigation_column_cost))
        .SetCostFunc(CostFunc.Exhaust("This")),
    ]
