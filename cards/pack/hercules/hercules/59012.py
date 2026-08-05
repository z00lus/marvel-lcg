from . import *


def GetAbilities() -> Sequence['Ability']:

    def generated_resources(effect: 'Effect', message: 'Message.WhenPlayerPayingResources') -> 'Resources':
        return Resources("G") * CountGifts(effect.GetInitiator())

    def available_resources(effect: 'Effect', message: 'Message.CheckPlayerCanPayCost') -> 'Resources|None':
        count = CountGifts(effect.GetInitiator())
        return Resources("G") * count if count else None

    return [
        AbilityFactory.DoGenerateResources(
            AbilityType.Resource,
            "This",
            res_fn=generated_resources,
        ).SetCostFunc(CostFunc.Exhaust("This")),
        AbilityFactory.CanGenerateResources(
            AbilityType.Resource,
            resources_fn=available_resources,
        ).SetCostFunc(CostFunc.Exhaust("This")),
    ]
