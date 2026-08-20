from . import *


def GetAbilities() -> Sequence['Ability']:
    def enter(effect: 'Effect', message: 'Message.AfterCardEnterPlay') -> None:
        Faces.PlaceCountersOn([effect.this], 1, 'spot', effect)

    def redirect(effect: 'Effect', message: 'Message.WhenUnitWouldTakeDamage') -> None:
        this = effect.this.CastTo(Minion)
        if this.GetCounters('spot'):
            Faces.RemoveCountersOn([this], 1, 'spot', effect)
            message.ChangeDealtToTarget(message.attacker, effect)
        else:
            Faces.PlaceCountersOn([this], 1, 'spot', effect)

    return [
        AbilityFactory.AfterCardEnterPlay(AbilityType.ForcedResponse, "This", enter),
        AbilityFactory.WhenUnitWouldTakeDamage(
            AbilityType.ForcedInterrupt,
            "This",
            redirect,
            is_from_attack=True,
        ),
    ]
