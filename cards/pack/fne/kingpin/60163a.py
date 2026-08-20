from . import *


def GetAbilities() -> Sequence['Ability']:
    def phase_begin(effect: 'Effect', message: 'Message.WhenPhaseBegin') -> None:
        this = effect.this.CastTo(Environment)
        required = Worlds.ConvertPerPlayerIconToInt("2*", effect)
        if this.GetCounters('support') < required:
            return
        villain = Worlds.FindVillain(effect)
        scheme = Worlds.FindMainScheme(effect)
        if villain:
            villain.card.Flip(effect, call_reveal=False)
        if scheme:
            scheme.Advance("2A", effect)
        this.card.Flip(effect, call_reveal=False)

    return [
        PublicSupportCounterAbility(),
        AbilityFactory.WhenVillainPhaseBegin(
            AbilityType.ForcedInterrupt,
            phase_begin,
            conditions=[lambda effect, message: effect.this.GetCounters('support') >= Worlds.ConvertPerPlayerIconToInt("2*", effect)],
        ),
    ]
