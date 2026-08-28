from . import *

# Contingency Planning


def CanAttachToMinionOrSideScheme(effect: 'Effect', face: 'CardFace') -> bool:
    Unused(effect)

    if not Upgrade.IsType(face):
        return False

    for ability in face.ability.Find(func_name="Play"):
        if not ability.selectors or not ability.selectors[0]:
            continue

        target_type = ability.selectors[0].selector_filter.finder.card_type
        if target_type is None:
            continue

        try:
            if issubclass(Minion, target_type) or \
                issubclass(SchemeSide2, target_type):
                return True
        except TypeError:
            continue

    return False


def GetAbilities() -> Sequence['Ability']:
    def contingency_planning(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        this = effect.this.CastTo(Upgrade)
        this.TuckCardUnderHere(effect.targets[0], effect)

    return [
        AbilityFactory.CanPlayThisUpgradeCard("YourIdentity"),
        *AbilityFactory.AttachedCardCanPlayLikeInHand(Upgrade),
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.Action,
            contingency_planning,
            conditions=[
                lambda effect, message:
                    effect.this.GetPlacedCardArea().GetSize() == 0
            ],
        ).SetTarget(
            CardFinder(card_type=Upgrade, check_effect_fn=CanAttachToMinionOrSideScheme),
            from_where=["YourHandCards"],
        ),
    ]
