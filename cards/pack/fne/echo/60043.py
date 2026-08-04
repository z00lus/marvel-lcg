from . import *

# American Sign Language


def GetAbilities() -> Sequence['Ability']:
    return [
        AbilityFactory.CanGenerateResources(
            AbilityType.HeroResource,
            Resources("G"),
            for_card=CardFinder(card_type=Event),
        ).SetCostFunc(CostFunc.Exhaust("This"))
        .AnyPlayerCanDoThis(),
    ]
