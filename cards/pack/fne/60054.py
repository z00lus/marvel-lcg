from . import *

# Stand Alone


def GetAbilities() -> Sequence['Ability']:

    def stand_alone(effect: 'Effect', message: 'Message.WhenUnitWouldAttack') -> None:
        Faces.ReadyAll([effect.GetInitiator().GetHero()], effect)

    return [
        AbilityFactory.WhenUnitAttackYou(
            AbilityType.HeroInterrupt,
            Enemy,
            stand_alone,
            conditions=[
                lambda effect, message:
                    len(effect.GetInitiator().GetControlAllies()) == 0 and
                    effect.GetInitiator().GetHero().CanReady()
            ],
        ).SetCostFunc(CostFunc.Exhaust("This")),
    ]
