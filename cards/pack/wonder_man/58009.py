from . import *

# Mr. Hollywood


def GetAbilities() -> Sequence['Ability']:

    def only_to_overpay(effect: 'Effect', message: 'Message.CheckPlayerCanPayCost') -> bool:
        return message.GetToPlayer().res_pool.Get().IsMatchCost(message.cost)

    return [
        AbilityFactory.CanGenerateResources(
            AbilityType.Resource,
            Resources("Y"),
            conditions=[only_to_overpay],
        ),
    ]
