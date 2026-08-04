from . import *

# Get Their Attention


def GetAbilities() -> Sequence['Ability']:

    def get_their_attention(effect: 'Effect', message: 'Message.WhenUnitWouldAttack') -> None:
        this = effect.this.CastTo(Event)
        this.RemoveThreatFromSchemes(effect.targets, 3, effect)

    return [
        AbilityFactory.WhenUnitWouldAttack(
            AbilityType.HeroInterrupt,
            Enemy,
            get_their_attention,
        ).SetPlay().SetLabel("defense", "thwart")
        .SetTarget(Scheme2),
    ]
