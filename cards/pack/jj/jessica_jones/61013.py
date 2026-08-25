from . import *


def GetAbilities() -> Sequence['Ability']:

    def reluctant_flier(effect: 'Effect', message: 'Message.WhenUnitWouldTakeDamage') -> None:
        message.PreventDamage("All", effect)
        effect.this.DealDamage([effect.GetInitiator().GetIdentity()], 1, effect)

    return [
        AbilityFactory.WhenUnitWouldTakeDamage(
            AbilityType.HeroInterrupt,
            "You",
            reluctant_flier,
            is_from_attack=True,
            conditions=[lambda effect, message: message.will_take_damage >= 3],
        ).SetCostFunc(CostFunc.Discard("This")).SetLabel("defense"),
    ]
