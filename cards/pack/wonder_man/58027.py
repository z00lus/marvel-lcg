from . import *

# Brother vs. Brother


def GetAbilities() -> Sequence['Ability']:

    def additional_attack_cost(effect: 'Effect', message: 'Message.WhenUnitWouldAttackUnit') -> None:
        player = message.attacker.GetControlByPlayer()
        discarded = player.AskDiscardFaces(player.hand_cards.GetAll(), (1, 1), effect)
        if not discarded:
            message.SetBeInstead(effect)

    return [
        AbilityFactory.WhenUnitWouldAttackUnit(
            AbilityType.NonKeyword,
            Friend,
            CardFinder(name="Grim Reaper", card_type=Minion),
            additional_attack_cost,
        ),
    ]
