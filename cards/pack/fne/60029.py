from . import *

# * Stick


def GetAbilities() -> Sequence['Ability']:

    def stick(effect: 'Effect', message: 'Message.WhenUnitUseBasicPower') -> None:
        this = effect.this.CastTo(Support)
        player = effect.GetInitiator()
        player.ChooseAbilities(
            effect,
            AbilityFactory.ForChoiceAbility(
                "Exhaust Stick: +1 to this basic power",
                lambda targets: message.GainValue(1, effect),
            ).SetCostFunc(CostFunc.Exhaust("This")),
            AbilityFactory.ForChoiceAbility(
                "-1 to this basic power: ready Stick",
                lambda targets: (
                    message.GainValue(-1, effect),
                    Faces.ReadyAll([this], effect),
                ),
            ),
        )

    return [
        AbilityFactory.CanPlayThisSupportCard(),
        AbilityFactory.WhenUnitUseBasicPower(
            AbilityType.Interrupt,
            CardFinder(card_type=Unit2, trait="MARTIAL ARTIST"),
            stick,
        ),
    ]
