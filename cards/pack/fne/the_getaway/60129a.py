from . import *


def GetAbilities() -> Sequence['Ability']:

    def ranged(effect: 'Effect', message: 'Message.WhenUnitWouldAttack') -> None:
        message.GainRanged(effect)

    def redirect_damage(effect: 'Effect', message: 'Message.WhenUnitWouldTakeDamage') -> None:
        this = effect.this.CastTo(Attachment)
        scheme = GetGetaway(effect)
        if not scheme:
            return
        damage = message.will_take_damage
        message.PreventDamage("All", effect)
        scheme.RemoveThreatFromSchemes(
            [scheme],
            damage,
            effect,
            ignore_crisis=True,
        )

    def threat_removed(effect: 'Effect', message: 'Message.AfterSchemeRemoveThreat') -> None:
        effect.this.card.Flip(effect)

    return [
        AbilityFactory.AttachToFaceWhenPutIntoPlay(Villain),
        AbilityFactory.WhenUnitAttackYou(
            AbilityType.NonKeyword,
            Villain,
            ranged,
        ),
        AbilityFactory.WhenUnitWouldTakeDamage(
            AbilityType.ForcedInterrupt,
            Villain,
            redirect_damage,
        ),
        AbilityFactory.AfterSchemeRemoveThreat(
            AbilityType.NonKeyword,
            GETAWAY,
            threat_removed,
            last_threat=True,
        ),
    ]
