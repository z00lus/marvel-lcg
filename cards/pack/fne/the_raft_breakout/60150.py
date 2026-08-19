from . import *


def GetAbilities() -> Sequence['Ability']:

    exhaust_selector = Select.From(
        "YouControlCharacter",
        range=(1, "All"),
    )
    exhaust_selector.selector_filter.AddParameter(canbe_exhaust=True)

    def valid_thwart_total(targets: Sequence['CardFace'], effect: 'Effect') -> bool:
        return sum(
            face.thwart for face in targets
            if HasThwart.IsType(face)
        ) >= 3

    def exhaust_characters(targets: Sequence['CardFace'], effect: 'Effect') -> bool:
        return Faces.ExhaustAll(targets, effect) == list(targets)

    return [
        AbilityFactory.AttachToFaceWhenPutIntoPlay("YourIdentity"),
        AbilityFactory.PlayersCannotAttackWhile("You", Enemy),
        AbilityFactory.PlayersCannotThwartWhile("You", Scheme2),
        AbilityFactory.PlayersCannotChangeForms(
            AbilityType.NonKeyword,
            "You",
            from_form=Hero,
            to_form=AlterEgo,
        ),
        AbilityFactory.PlayerActionToDiscardThis(
            AbilityType.HeroAction,
        ).SetName("Spend 3 resources to discard Imprisoned").SetCost(Cost("3")),
        AbilityFactory.PlayerActionToDiscardThis(
            AbilityType.HeroAction,
        ).SetName("Exhaust characters with at least 3 total THW to discard Imprisoned")
        .SetCostFunc(CostFunc.Custom(
            exhaust_selector,
            exhaust_characters,
            validate_fn=valid_thwart_total,
        )),
        AbilityFactory.WhenCardBecomeBoost("This", RevealThisCard),
    ]
