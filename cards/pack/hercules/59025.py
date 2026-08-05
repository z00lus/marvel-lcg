from . import *


def GetAbilities() -> Sequence['Ability']:

    def additional_cost(targets: Sequence['CardFace'], effect: 'Effect') -> bool:
        identity = effect.GetInitiator().GetIdentity()
        if identity.HasTrait("ETERNAL"):
            return True
        return bool(Faces.GiveStatus([identity], "Confused", effect))

    return [
        AbilityFactory.CanPlayThisAllyCard().SetCostFunc(
            CostFunc.Custom(None, additional_cost)
        ),
    ]
