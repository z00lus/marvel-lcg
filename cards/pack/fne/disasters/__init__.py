from cards.pack import *


def GetDisasters(effect: 'Effect') -> List['Environment']:
    return Worlds.FindCardsOnField(effect, card_type=Environment, trait="DISASTER")


def ChooseDisaster(player: 'Player', effect: 'Effect') -> 'Environment|None':
    disasters = GetDisasters(effect)
    if not disasters:
        return None
    chosen = disasters[0] if len(disasters) == 1 else player.AskChooseFace(
        disasters,
        effect,
        prompt="Choose a DISASTER environment",
    )
    return chosen.CastTo(Environment) if chosen else None


def DisasterEnvironmentAbilities(
    resource_cost: str,
    bonus_trait: 'CardFace.TRAITS|None'=None,
    *,
    bonus_tough: bool=False,
) -> List['Ability']:
    exhaust_cost = CostFunc.Exhaust("YouControlUnit")

    def remove_with_resources(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        Faces.RemoveCountersOn([effect.this], 1, 'civilian', effect)

    def remove_with_character(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        exhausted = exhaust_cost.return_exhausted_cards
        if not exhausted:
            return
        character = exhausted[-1]
        value = 2 if (
            (bonus_trait and character.HasTrait(bonus_trait)) or
            (bonus_tough and Unit2.IsType(character) and character.CastTo(Unit2).HasStatus("Tough"))
        ) else 1
        Faces.RemoveCountersOn([effect.this], value, 'civilian', effect)

    return [
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.HeroAction,
            remove_with_resources,
        ).SetCost(Cost(resource_cost)).SetTarget("This", has_counter='civilian'),
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.HeroAction,
            remove_with_character,
        ).SetCostFunc(exhaust_cost).SetTarget("This", has_counter='civilian'),
    ]
