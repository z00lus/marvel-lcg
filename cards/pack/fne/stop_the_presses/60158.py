from . import *


def GetAbilities() -> Sequence['Ability']:

    def revealed(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        player = message.GetToPlayer()
        supports = [
            support for support in GetDailyBugleSupports(effect)
            if support.CanExhaust() and support.GetCounters(STAMINA) > 0
        ]

        def exhaust_and_remove_stamina(targets: Sequence['CardFace']) -> None:
            if targets:
                support = targets[0].CastTo(Support)
                Faces.ExhaustAll([support], effect)
                RemoveStamina(support, effect)

        def place_threat(targets: Sequence['CardFace']) -> None:
            main_scheme = Worlds.FindMainScheme(effect)
            if main_scheme:
                effect.this.PlaceThreatOnSchemes([main_scheme], 2, effect)

        player.ChooseAbilities(
            effect,
            AbilityFactory.ForChoiceAbility(
                "Exhaust a DAILY BUGLE support and remove 1 stamina",
                exhaust_and_remove_stamina,
            ).SetTarget(supports, not_move=True),
            AbilityFactory.ForChoiceAbility(
                "Place 2 threat on the main scheme",
                place_threat,
            ),
        )

    def boost(effect: 'Effect', message: 'Message.WhenCardBecomeBoost') -> None:
        player = message.GetToPlayer()
        supports = [
            support for support in GetDailyBugleSupports(effect)
            if support.CanExhaust()
        ]
        if not player or not supports:
            return
        support = supports[0] if len(supports) == 1 else player.AskChooseFace(
            supports,
            effect,
            prompt="Choose a DAILY BUGLE support to exhaust",
        )
        if support:
            Faces.ExhaustAll([support], effect)

    return [
        AbilityFactory.WhenThisRevealed(None, revealed),
        AbilityFactory.WhenCardBecomeBoost("This", boost),
    ]
