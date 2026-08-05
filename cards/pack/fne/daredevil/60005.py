from . import *

# Radar Sense


def GetAbilities() -> Sequence['Ability']:

    def radar_sense(effect: 'Effect', message: 'Message.AfterUnitAttackUnit') -> None:
        this = effect.this.CastTo(Upgrade)
        target = this.GetBindFace().CastTo(Enemy)
        Faces.DiscardAll([this], effect)
        this.DealDamage([target], 3, effect)

    return [
        AbilityFactory.CanPlayThisUpgradeCard(Enemy),
        AbilityFactory.AfterUnitAttackUnit(
            AbilityType.Response,
            "You",
            "AttachedEnemy",
            radar_sense,
        ).SetLabel("attack"),
    ]
