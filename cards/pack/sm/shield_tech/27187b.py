from . import *

# Shock Knuckles

def GetAbilities() -> Sequence['Ability']:

    def shock_knuckles(effect: 'Effect', message: 'Message.AfterUnitAttackEnd') -> None:
        this = effect.this.CastTo(Upgrade)
        Unused(this)

        face = Worlds.DiscardEncounterTopCard(effect)
        if face:
            if FacesCounter.CountTotalBoostIcons([face]) <= 1:
                Faces.GiveStatus(effect.targets, "Stunned", effect)


    return [
        *AbilityFactory.GiveKeywordToAttached(
            Hero,
            attack=1,
        ),
        AbilityFactory.AfterUnitMakeBasicAttack(
            AbilityType.HeroResponse,
            "YourHero",
            shock_knuckles,
            against_who=Enemy
        ).SetTarget("Attacked", canbe_stunned=True),
    ]
