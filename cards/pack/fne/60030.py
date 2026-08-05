from . import *

# Contingency Planning


def GetAbilities() -> Sequence['Ability']:

    def can_attach_to_minion_or_side_scheme(effect: 'Effect', face: 'CardFace') -> bool:
        targets = [*Worlds.GetSideSchemes(effect), *Worlds.GetOnFieldEnemies(effect)]
        return any(
            (Minion.IsType(target) or SchemeSide2.IsType(target)) and
            face.CanAttachTo(target)
            for target in targets
        )

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
            CardFinder(card_type=Upgrade, check_effect_fn=can_attach_to_minion_or_side_scheme),
            from_where=["YourHandCards"],
        ),
    ]
