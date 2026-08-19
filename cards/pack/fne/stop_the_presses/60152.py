from . import *


def GetAbilities() -> Sequence['Ability']:

    def restore_stamina(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        supports = effect.cost_func.Get(CostFunc.Exhaust).return_exhausted_cards
        Faces.PlaceCountersOn(supports, 1, STAMINA, effect)

    return [
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.AlterEgoAction,
            restore_stamina,
        ).SetCostFunc(CostFunc.Exhaust(
            DAILY_BUGLE_SUPPORT,
            from_where=["YouControlCards"],
        )).AnyPlayerCanDoThis(),
    ]
