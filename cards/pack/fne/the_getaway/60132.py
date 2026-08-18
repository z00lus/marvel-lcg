from . import *


def GetAbilities() -> Sequence['Ability']:

    def revealed(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        this = effect.this.CastTo(Treachery)
        player = message.GetToPlayer()
        scheme = GetGetaway(effect)
        if not scheme:
            return
        for _ in range(GetSpeed(effect)):
            player.ChooseAbilities(
                effect,
                AbilityFactory.ForChoiceAbilityWithCost(
                    Cost("1"),
                    "Spend 1 resource of any type",
                ),
                AbilityFactory.ForChoiceAbility(
                    "Place 1 threat on the main scheme",
                    lambda targets: this.PlaceThreatOnSchemes(
                        [scheme],
                        1,
                        effect,
                    ),
                ),
            )

    return [AbilityFactory.WhenThisRevealed(None, revealed)]
