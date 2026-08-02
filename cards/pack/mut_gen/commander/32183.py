from . import *


# Group Assault

def GetAbilities() -> Sequence['Ability']:
    def group_assault(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        def prevent_consequential(effect2: 'Effect', attack: 'Message.WhenUnitWouldAttack') -> None:
            attack.DoesNotTakeConsequentialDamage(effect2)

        effect.this.effect.RegisterTemp(
            AbilityFactory.WhenUnitMakeAttack(
                AbilityType.Temp0,
                Ally,
                prevent_consequential,
            ),
            unregister_after_exec=False,
            until_phase_end=True,
        )

    return [
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.HeroAction,
            group_assault,
        ).SetCostFunc(CostFunc.RemoveFromGame("This"))
        .SetCostFunc(CostFunc.RemoveFromCampaignLog("This")),
    ]
