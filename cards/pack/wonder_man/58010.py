from . import *

# Signature Sunglasses


def GetAbilities() -> Sequence['Ability']:

    def signature_sunglasses(effect: 'Effect', message: 'Message.AfterUnitChangeForm') -> None:
        player = effect.GetInitiator()
        physiology = FindIonicPhysiology(effect)
        tucked = GetIonicCards(effect)
        tuckable = GetEnergyCardsInDiscard(effect, include_resources=True)
        can_tuck = bool(physiology and physiology.GetPlacedCardArea().GetSize() < 3 and tuckable)

        player.ChooseAbilities(
            effect,
            AbilityFactory.ForChoiceAbility(
                "Tuck an energy event or resource under Ionic Physiology",
                lambda targets: TuckUnderIonic(effect, targets),
                condition=can_tuck,
            ).SetTarget(tuckable),
            AbilityFactory.ForChoiceAbility(
                "Add a tucked card to your hand",
                lambda targets: Faces.AddToHand(targets, player, effect),
                condition=bool(tucked),
            ).SetTarget(tucked),
        )

    return [
        AbilityFactory.AfterUnitChangeForm(
            AbilityType.Response,
            "You",
            signature_sunglasses,
        ),
    ]
