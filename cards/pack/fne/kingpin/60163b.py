from . import *


def GetAbilities() -> Sequence['Ability']:
    def replace_boost(effect: 'Effect', message: 'Message.WhenEnemyWouldBeGivenBoostCard') -> None:
        this = effect.this.CastTo(Environment)
        required = Worlds.ConvertPerPlayerIconToInt("1*", effect)
        message.SetBeInstead(effect)
        Faces.RemoveCountersOn([this], required, 'support', effect)

    return [
        PublicSupportCounterAbility(),
        AbilityFactory.WhenEnemyWouldBeGivenBoostCard(
            AbilityType.ForcedInterrupt,
            Enemy,
            replace_boost,
            conditions=[lambda effect, message: effect.this.GetCounters('support') >= Worlds.ConvertPerPlayerIconToInt("1*", effect)],
        ),
    ]
