from . import *

# Jet Belt


def GetAbilities() -> Sequence['Ability']:

    def can_generate(effect: 'Effect', message: 'Message.CheckPlayerCanPayCost') -> 'Resources|None':
        paying_for = message.paying_for_effect.this
        if Event.IsType(paying_for) or GetIonicCards(effect):
            return Resources("Y")
        return None

    def pay_jet_belt_cost(targets: Sequence['CardFace'], effect: 'Effect') -> bool:
        message = effect.GetBindMessage(Message.WhenPlayerPayingResources)
        if targets:
            return Faces.DiscardAll(targets, effect) == list(targets)
        return Event.IsType(message.for_effect.this)

    return [
        AbilityFactory.DoGenerateResources(
            AbilityType.HeroResource,
            "This",
            res_fn=lambda effect, message: Resources("Y"),
        ).SetCostFunc(CostFunc.Custom(
            Select.From(lambda effect: GetIonicCards(effect), range=(0, 1)),
            pay_jet_belt_cost,
        ))
        .SetCostFunc(CostFunc.Exhaust("This")),
        AbilityFactory.CanGenerateResources(
            AbilityType.HeroResource,
            resources_fn=can_generate,
        ),
    ]
