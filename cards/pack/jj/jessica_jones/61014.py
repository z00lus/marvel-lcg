from . import *


def GetAbilities() -> Sequence['Ability']:

    def attach_stakeout(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        this = effect.this.CastTo(Upgrade)
        this.AttachTo2(effect.targets[0], effect)

    def increase_thwart(effect: 'Effect', message: 'Message.WhenSchemeBeingThwart') -> None:
        message.GainThwartForThisThwart(2, effect)

    def collect_evidence(effect: 'Effect', message: 'Message.WhenSchemeBeDefeated') -> None:
        PlaceEvidence(2, effect)

    return [
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.Action,
            attach_stakeout,
            conditions=[lambda effect, message: not effect.this.card.state.is_attached],
        ).SetTarget(CardFinder(card_type=EncounterSideScheme, is_permanent=False)),
        AbilityFactory.WhenUnitThwartScheme(
            AbilityType.Interrupt,
            None,
            increase_thwart,
            which_card_be_thwart="AttachedScheme",
        ),
        AbilityFactory.WhenSchemeBeDefeated(
            AbilityType.ForcedResponse,
            "AttachedScheme",
            collect_evidence,
            conditions=[
                lambda effect, message: message.would_defeat_message.being_message is not None,
            ],
        ),
    ]
