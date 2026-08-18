from . import *


def GetAbilities() -> Sequence['Ability']:

    def revealed(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        this = effect.this.CastTo(Treachery)
        player = message.GetToPlayer()
        for _ in range(GetSpeed(effect)):
            player.ChooseAbilities(
                effect,
                AbilityFactory.ForChoiceAbility(
                    "Exhaust a character you control",
                    targets_is_exhaust_cost=True,
                ).SetCostFunc(CostFunc.Exhaust("YouControlUnit")),
                AbilityFactory.ForChoiceAbility(
                    "Take 1 indirect damage",
                    lambda targets:
                        player.GetIdentity().TakeIndirectDamage(this, 1, effect),
                ),
            )

    return [AbilityFactory.WhenThisRevealed(None, revealed)]
