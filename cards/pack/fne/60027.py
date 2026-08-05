from . import *

# Move in Shadow


def GetAbilities() -> Sequence['Ability']:

    def move_in_shadow(effect: 'Effect', message: 'Message.AfterPlayerPlayedCard') -> None:
        effect.this.RemoveThreatFromSchemes(effect.targets, 1, effect)

    return [
        AbilityFactory.ReduceCostToPlayThis(
            1,
            your_identity_has_traits=["MARTIAL ARTIST", "SPY"],
        ),
        AbilityFactory.CanPlayThisUpgradeCard("YourIdentity"),
        AbilityFactory.AfterPlayerPlayedCard(
            AbilityType.Response,
            "You",
            CardFace,
            move_in_shadow,
        ).SetLabel("thwart").SetTarget(Scheme2),
    ]
