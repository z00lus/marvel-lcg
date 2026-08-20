from . import *


def GetAbilities() -> Sequence['Ability']:
    def consolidate(effect: 'Effect', message: 'Message.AfterUnitBeDefeated') -> None:
        villain = Worlds.FindVillain(effect)
        if villain:
            villain.GiveBoostCard(message.trigger, effect)

    return [
        AbilityFactory.AfterUnitBeDefeated(
            AbilityType.ForcedResponse,
            Minion,
            consolidate,
        ),
    ]
