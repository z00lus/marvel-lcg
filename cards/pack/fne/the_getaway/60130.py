from . import *


def GetAbilities() -> Sequence['Ability']:
    speed_event = OnEvent.Counter(GETAWAY, 'speed')
    return [
        AbilityFactory.ThisGainKeyword(
            lambda effect, ui: GetSpeed(effect) >= 3,
            toughness=1,
            change_on_event=speed_event,
        ),
        AbilityFactory.ThisGainKeyword(
            lambda effect, ui: GetSpeed(effect) >= 6,
            quickstrike=1,
            change_on_event=speed_event,
        ),
        AbilityFactory.ThisGainKeyword(
            lambda effect, ui: GetSpeed(effect) >= 9,
            surge=1,
            change_on_event=speed_event,
        ),
    ]
