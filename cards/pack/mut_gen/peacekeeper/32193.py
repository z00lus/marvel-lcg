from . import *


# Rescue Operation

def GetAbilities() -> Sequence['Ability']:
    def rescue_operation(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        def prevent_consequential(effect2: 'Effect', thwart: 'Message.WhenUnitWouldThwart') -> None:
            thwart.DoesNotTakeConsequentialDamage(effect2)

        effect.this.effect.RegisterTemp(
            AbilityFactory.WhenUnitMakeThwart(
                AbilityType.Temp0,
                Ally,
                None,
                prevent_consequential,
            ),
            unregister_after_exec=False,
            until_phase_end=True,
        )

    return [
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.HeroAction,
            rescue_operation,
        ).SetCostFunc(CostFunc.RemoveFromGame("This"))
        .SetCostFunc(CostFunc.RemoveFromCampaignLog("This")),
    ]
