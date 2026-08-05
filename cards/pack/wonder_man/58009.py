from . import *

# Mr. Hollywood


def GetAbilities() -> Sequence['Ability']:

    def only_to_overpay(targets: Sequence['CardFace'], effect: 'Effect') -> bool:
        message = effect.GetBindMessage(Message.WhenPlayerPayingResources)
        for_effect = message.for_effect
        target = message.for_target
        payment = for_effect.checker.cost_for_different_target.GetPayment(target)

        paid_without_this = Resources("0")
        for paying_effect in for_effect.context.paid_this_res_effects:
            if paying_effect == message.by_effect:
                continue
            for payment_info in payment.payments:
                if paying_effect in payment_info:
                    paid_without_this += Resources.FromText(payment_info[paying_effect])
                    break

        return paid_without_this.IsMatchCost(payment.cost)

    return [
        AbilityFactory.CanGenerateResources(
            AbilityType.Resource,
            Resources("Y"),
            is_play_card=True,
        ).SetCostFunc(CostFunc.Custom(None, only_to_overpay)),
    ]
