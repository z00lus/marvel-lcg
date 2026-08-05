from . import *


def GetAbilities() -> Sequence['Ability']:

    def defeat_the_hydra_revealed(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        this = effect.this.CastTo(Attachment)
        player = message.GetToPlayer()
        minion = Find.FindAndReveal(
            effect,
            player,
            finder=CardFinder(
                card_type=Minion,
                non_trait="ELITE",
                check_face_fn=lambda face: face.printed_health >= 6,
            ),
        )
        if minion:
            this.HealthUnits([minion], "All", effect)
            this.AttachTo2(minion, effect)

    def prevent_non_hercules_damage(effect: 'Effect', message: 'Message.WhenUnitWouldTakeDamage') -> None:
        message.PreventDamage("All", effect)

    def is_not_hercules_attack(effect: 'Effect', message: 'Message.WhenUnitWouldTakeDamage') -> bool:
        return not (
            message.IsFromAttack() and
            message.source.IsName("Hercules", check_all_face=True)
        )

    def complete_labor(effect: 'Effect', message: 'Message.WhenUnitBeDefeated') -> None:
        Faces.AddToVictoryDisplay([effect.this], effect)

    return [
        AbilityFactory.WhenThisRevealed(None, defeat_the_hydra_revealed),
        *AbilityFactory.GiveKeywordToAttached(
            Minion,
            health=6,
            trait="ELITE",
        ),
        AbilityFactory.WhenUnitWouldTakeDamage(
            AbilityType.ForcedInterrupt,
            "AttachedMinion",
            prevent_non_hercules_damage,
            conditions=[is_not_hercules_attack],
        ),
        AbilityFactory.WhenUnitBeDefeated(
            AbilityType.Interrupt,
            "AttachedMinion",
            complete_labor,
        ),
    ]
