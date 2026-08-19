from . import *


def GetAbilities() -> Sequence['Ability']:
    def after_attack(effect: 'Effect', message: 'Message.AfterUnitAttackUnit') -> None:
        if message.excess_damage:
            scheme = Worlds.FindMainScheme(effect)
            if scheme:
                effect.this.PlaceThreatOnSchemes([scheme], message.excess_damage, effect)

    def boost(effect: 'Effect', message: 'Message.WhenCardBecomeBoost') -> None:
        if not isinstance(message.being_message, Message.WhenUnitBeingAttack):
            return
        effect.this.effect.RegisterTemp(
            AbilityFactory.AfterUnitAttackUnit(
                AbilityType.Temp0,
                message.being_message.would_atk_message.attacker,
                Unit2,
                after_attack,
            ),
            unregister_after_exec=True,
            until_event_end=message.being_message.would_atk_message,
        )

    return [
        AbilityFactory.AfterUnitAttackUnit(
            AbilityType.ForcedResponse,
            "This",
            Unit2,
            after_attack,
        ),
        AbilityFactory.WhenCardBecomeBoost("This", boost),
    ]
