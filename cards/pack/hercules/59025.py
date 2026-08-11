from . import *


def GetAbilities() -> Sequence['Ability']:

    def can_pay_additional_cost(targets: Sequence['CardFace'], effect: 'Effect') -> bool:
        identity = effect.GetInitiator().GetIdentity()
        return identity.HasTrait("ETERNAL") or identity.CanbeConfused()

    def additional_cost(targets: Sequence['CardFace'], effect: 'Effect') -> bool:
        identity = effect.GetInitiator().GetIdentity()
        if identity.HasTrait("ETERNAL"):
            return True
        return bool(Faces.GiveStatus([identity], "Confused", effect))

    return [
        AbilityFactory.CanPlayThisAllyCard().SetCostFunc(
            CostFunc.Custom(
                None,
                additional_cost,
                validate_fn=can_pay_additional_cost,
            )
        ),
    ]
