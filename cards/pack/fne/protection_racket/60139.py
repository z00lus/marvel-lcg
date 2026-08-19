from . import *


def GetAbilities() -> Sequence['Ability']:
    def revealed(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        effect.this.CastTo(Ally).PutIntoPlay(message.GetGaveToPlayer(), effect, under_control=True)
        ThisCardGainSurge(effect)

    def left_play(effect: 'Effect', message: 'Message.AfterCardLeavePlay') -> None:
        scheme = Worlds.FindMainScheme(effect)
        if scheme:
            effect.this.PlaceThreatOnSchemes([scheme], 4, effect)

    return [
        AbilityFactory.WhenThisRevealed(None, revealed).SetCannotBeCancel(),
        AbilityFactory.AfterCardLeavePlay(AbilityType.ForcedInterrupt, "This", left_play),
    ]
