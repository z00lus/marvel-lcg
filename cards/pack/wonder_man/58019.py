from . import *

# Stronger Together

def GetAbilities() -> Sequence['Ability']:

    def stronger_together(effect: 'Effect', message: 'Message.WhenUnitWouldTakeDamage') -> None:
        this = effect.this.CastTo(Event)
        Unused(this)

        initiator = effect.GetInitiator()

        value = initiator.GetHero().defense
        message.ReduceDamage(value, effect)


    return [
        AbilityFactory.WhenUnitWouldTakeDamage(
            AbilityType.HeroInterrupt,
            Unit2,
            stronger_together,
            conditions=[
                lambda effect, message:
                    message.trigger != effect.GetInitiator().GetHero()
            ],
        ).SetPlay().SetLabel()
        .SetTarget("Trigger", share_trait_with_your_hero=True),
    ]
