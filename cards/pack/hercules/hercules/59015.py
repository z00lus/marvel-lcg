from . import *


def GetAbilities() -> Sequence['Ability']:

    def hercs_helm(effect: 'Effect', message: 'Message.WhenUnitWouldAttack') -> None:
        def prevent_damage(effect2: 'Effect', damage_message: 'Message.WhenUnitWouldTakeDamage') -> None:
            damage_message.PreventDamage(1, effect2)

        effect.this.effect.RegisterTemp(
            AbilityFactory.WhenUnitWouldTakeDamage(
                AbilityType.Temp0,
                None,
                prevent_damage,
                is_from_attack=message,
            ),
            unregister_after_exec=True,
            until_event_end=message,
        )

    return [
        AbilityFactory.WhenUnitWouldAttack(
            AbilityType.HeroInterrupt,
            Villain,
            hercs_helm,
        ).SetCostFunc(CostFunc.Exhaust("This")).SetLabel("defense"),
    ]
