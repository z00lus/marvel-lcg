from . import *
from cards.pack.gmw.campaign import ExpertCampaignAddHandCardToTheCollectionAfterSetup

# The Grand Collection

def GetAbilities() -> Sequence['Ability']:

    def the_grand_collection(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        this = effect.this.CastTo(MainScheme)
        Unused(this)

        Faces.DiscardAll(effect.targets, effect, into_area="Owner")


    def the_grand_collection_cost(targets: Sequence['CardFace'], effect: 'Effect'):
        initiator = effect.GetInitiator()
        effects = initiator.ChooseAbilities(
            effect,
            AbilityFactory.ForChoiceAbility(
                "Exhaust your hero",
                lambda targets:
                    Faces.ExhaustAll(targets, effect)
            ).SetTarget("YourHero", canbe_exhaust=True),
            AbilityFactory.ForChoiceAbilityWithCost(
                Cost("2"),
            ),
        )
        return effects != []

    return [
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.HeroAction,
            the_grand_collection
        ).SetCostFunc(CostFunc.Custom(None, the_grand_collection_cost))
        .SetTarget(lambda effect: GetTheCollection(effect).deck.Get())
        .LimitOncePerRoundPerPlayer(),
        AbilityFactory.AfterCardsMoved(
            AbilityType.NonKeywordBold,
            None,
            lambda effect, message:
                Worlds.SetGameOver(False, effect),
            conditions=[
                lambda effect, message:
                    GetTheCollection(effect).deck in message.into_areas and \
                    GetTheCollection(effect).deck.GetSize() >= 5 * Worlds.GetPlayerNumIcon(effect),
            ]
        ),
        AbilityFactory.IfThisSchemeStageIsCompletedPlayersLoseTheGame(),
        ExpertCampaignAddHandCardToTheCollectionAfterSetup(),
    ]
