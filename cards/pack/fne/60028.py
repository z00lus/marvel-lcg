from . import *

# Stealth Training


def GetAbilities() -> Sequence['Ability']:

    def exactly_defeated_side_scheme(effect: 'Effect', message: 'Message.AfterUnitThwartEnd') -> bool:
        for after in message.after_thw_messages:
            property = after.would_thw_message.property
            attempted = 1 if property.is_divided else property.GetThwart(message.trigger)
            if (
                SchemeSide2.IsType(after.scheme) and
                after.scheme.threat == 0 and
                after.remove_threat == attempted
            ):
                return True
        return False

    def stealth_training(effect: 'Effect', message: 'Message.AfterUnitThwartEnd') -> None:
        Faces.GiveStatus(effect.targets, "Stunned", effect)

    return [
        AbilityFactory.CanPlayThisUpgradeCard("Players"),
        AbilityFactory.AfterUnitThwartEnd(
            AbilityType.Response,
            "You",
            stealth_training,
            conditions=[exactly_defeated_side_scheme],
        ).SetCostFunc(CostFunc.Exhaust("This")).SetTarget(Enemy, canbe_stunned=True),
    ]
