from . import *

# Superior Taste


def GetAbilities() -> Sequence['Ability']:

    def superior_taste(effect: 'Effect', message: 'Message.AfterSchemeRemoveThreat') -> None:
        this = effect.this.CastTo(Upgrade)
        scheme = this.GetBindFace().CastTo(Scheme2)
        Faces.DiscardAll([this], effect)
        this.RemoveThreatFromSchemes([scheme], 2, effect)

    return [
        AbilityFactory.CanPlayThisUpgradeCard(Scheme2),
        AbilityFactory.AfterSchemeRemoveThreat(
            AbilityType.Response,
            "AttachedScheme",
            superior_taste,
            by_who="You",
            by_thwart=True,
        ).SetLabel("thwart"),
    ]
