from . import *

# * Shark-Girl: Iara Dos Santos

def GetAbilities() -> Sequence['Ability']:

    def shark_girl(effect: 'Effect', message: 'Message.WhenCalculateAttackDamage') -> int:
        this = effect.this.CastTo(Ally)
        Unused(this)

        return len(message.target.GetAttachedUpgrades())


    return [
        *AbilityFactory.UnitGetATKWhileAttacking(
            AbilityType.NonKeywordStar,
            "This",
            Enemy,
            shark_girl
        ),
    ]
