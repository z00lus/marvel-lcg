from . import *

# Jarvis


def GetAbilities() -> Sequence['Ability']:

    def jarvis(effect: 'Effect', message: 'Message.AfterUnitChangeForm') -> None:
        identity = message.trigger.CastTo(Identity)
        chooser = effect.GetInitiator()
        statuses = identity.components.status.GetDeck().GetAll()

        chooser.ChooseAbilities(
            effect,
            AbilityFactory.ForChoiceAbility(
                "That identity gets +2 REC until the end of the phase",
                lambda targets: identity.GainUntilPhaseEnd(effect, recover=2),
            ),
            AbilityFactory.ForChoiceAbility(
                "Discard a status card from that identity",
                lambda targets: Faces.DiscardAll(targets, effect),
                condition=bool(statuses),
            ).SetTarget(statuses, canbe_discard=True),
        )

    return [
        AbilityFactory.AfterUnitChangeForm(
            AbilityType.Response,
            CardFinder(card_type=Identity),
            jarvis,
            from_form=CardFinder(card_type=Hero, trait="AVENGER"),
            to_form=AlterEgo,
        ).SetCostFunc(CostFunc.Exhaust("This")),
    ]
