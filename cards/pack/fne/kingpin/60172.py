from . import *


def GetAbilities() -> Sequence['Ability']:
    def enter(effect: 'Effect', message: 'Message.AfterCardEnterPlay') -> None:
        Faces.PlaceCountersOn([effect.this], 2, 'stilt', effect)

    def prevent(effect: 'Effect', message: 'Message.WhenUnitWouldTakeDamage') -> None:
        message.SetBeInstead(effect)
        Faces.RemoveCountersOn([effect.this], 1, 'stilt', effect)

    counter_value = lambda effect, ui: effect.this.GetCounters('stilt')
    return [
        AbilityFactory.AfterCardEnterPlay(AbilityType.ForcedResponse, "This", enter),
        AbilityFactory.ThisGainKeyword(
            counter_value,
            attack=1,
            scheme=1,
            change_on_event=OnEvent.Counter("This", "stilt"),
        ),
        AbilityFactory.WhenUnitWouldTakeDamage(
            AbilityType.ForcedInterrupt,
            "This",
            prevent,
            conditions=[lambda effect, message: effect.this.GetCounters('stilt') > 0],
        ),
    ]
