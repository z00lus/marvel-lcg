from . import *


def GetAbilities() -> Sequence['Ability']:
    def after_attack(effect: 'Effect', message: 'Message.AfterUnitAttackUnit') -> None:
        message.attacker.TakeDamage(effect.this, 1, effect)
        PlaceThreatHere(effect)

    standard = AbilityFactory.AfterUnitAttackUnit(
        AbilityType.ForcedResponse,
        Unit2,
        Unit2,
        after_attack,
        conditions=[lambda effect, message: not Worlds.IsExpert(effect)],
    ).LimitOncePerPhase()
    expert = AbilityFactory.AfterUnitAttackUnit(
            AbilityType.ForcedResponse,
            Unit2,
            Unit2,
            after_attack,
            conditions=[lambda effect, message: Worlds.IsExpert(effect)],
        )
    return [standard, expert]
