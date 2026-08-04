from . import *

# * Grim Reaper


def GetAbilities() -> Sequence['Ability']:

    def grim_reaper(effect: 'Effect', message: 'Message.AfterUnitDefeatedUnit') -> None:
        message.target.GetControlByPlayer().DealEncounterCards(1, effect)

    return [
        AbilityFactory.AfterUnitAttackAndDefeatUnit(
            AbilityType.ForcedResponse,
            "This",
            Ally,
            grim_reaper,
        ),
    ]
