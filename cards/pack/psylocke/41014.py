from . import *

# Concussive Blow

def GetAbilities() -> Sequence['Ability']:

    def concussive_blow(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        this = effect.this.CastTo(Event)
        Unused(this)

        Faces.GiveStatus(effect.targets, "Confused", effect)
        if effect.GetPaidResources().HasColor("R"):
            this.DealDamage(effect.targets, 3, effect)


    return [
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.HeroAction,
            concussive_blow
        ).SetPlay().SetLabel('attack')
        .SetTarget(
            Enemy,
            affects_target_if=(
                Condition.TargetCanBeConfused,
                Condition.TargetCanTakeDamage,
            ),
        ),
    ]
