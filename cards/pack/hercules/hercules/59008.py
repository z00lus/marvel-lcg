from . import *


def GetAbilities() -> Sequence['Ability']:

    def redirect_attack(effect: 'Effect', message: 'Message.WhenUnitWouldAttackUnit') -> None:
        message.ChangeTarget(effect.this.CastTo(Ally), effect)

    def draw_card(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        effect.GetInitiator().DrawUp(1, effect)

    return [
        AbilityFactory.WhenUnitWouldAttackUnit(
            AbilityType.ForcedInterrupt,
            Minion,
            "YourIdentity",
            redirect_attack,
        ),
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.Action,
            draw_card,
        ).SetCostFunc(CostFunc.Exhaust("This")),
    ]
