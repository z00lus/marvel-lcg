from . import *

# Energy Siphon


def GetAbilities() -> Sequence['Ability']:

    def generated_resources(effect: 'Effect', message: 'Message.WhenPlayerPayingResources') -> 'Resources':
        damage = effect.cost_func.Get(CostFunc.TakeDamageUpTo).return_damage
        return Resources("Y") * (1 + damage)

    return [
        AbilityFactory.DoDiscardThisToGenerateResources(
            AbilityType.HeroInterrupt,
            res_fn=generated_resources,
        ).SetCostFunc(CostFunc.TakeDamageUpTo(3, "YourIdentity")),
        AbilityFactory.CheckThisCanDropPay(
            Resources("YYYY"),
            spend_this_only_in_hero_form=True,
        ),
    ]
