from . import *

# Tackle

def GetAbilities() -> Sequence['Ability']:

    def tackle(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        this = effect.this.CastTo(Event)
        Unused(this)

        Faces.GiveStatus(effect.targets, "Stunned", effect)
        if effect.GetPaidResources().HasColor("R"):
            this.DealDamage(effect.targets, 3, effect)


    return [
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.HeroAction,
            tackle
        ).SetPlay().SetLabel('attack')
        .SetTarget(
            Enemy,
            affects_target_if=(
                Condition.TargetCanBeStunned,
                Condition.TargetCanTakeDamage,
            ),
        ),
    ]
