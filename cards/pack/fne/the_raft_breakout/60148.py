from . import *


def GetAbilities() -> Sequence['Ability']:

    def proxima_midnight(effect: 'Effect', message: 'Message.WhenUnitWouldAttack') -> None:
        this = effect.this.CastTo(Minion)
        player = message.GetAgainstPlayer()
        if not player:
            return
        player.ChooseAbilities(
            effect,
            AbilityFactory.ForChoiceAbility(
                "Place 1 threat on the main scheme",
                lambda targets: this.PlaceThreatOnSchemes("MainScheme", 1, effect),
            ),
            AbilityFactory.ForChoiceAbility(
                "Proxima Midnight gets +2 ATK for this attack",
                lambda targets: message.GainAttackForThisAttack(2, effect),
            ),
        )

    return [
        AbilityFactory.WhenUnitWouldAttack(
            AbilityType.ForcedInterrupt,
            "This",
            proxima_midnight,
        ),
    ]
