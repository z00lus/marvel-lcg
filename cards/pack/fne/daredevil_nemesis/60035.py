from . import *

# Stolen Sai


def GetAbilities() -> Sequence['Ability']:

    def stolen_sai_action(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        this = effect.this.CastTo(Attachment)
        elektra = Worlds.FindCardOnField(effect, name="Elektra", card_type=Ally)
        choices = [
            AbilityFactory.ForChoiceAbility(
                "Discard Stolen Sai",
                lambda targets: Faces.DiscardAll([this], effect),
            )
        ]
        if elektra and this.CanAttachTo(elektra):
            choices.insert(
                0,
                AbilityFactory.ForChoiceAbility(
                    "Attach Stolen Sai to Elektra",
                    lambda targets: this.AttachTo2(elektra, effect),
                ),
            )
        effect.GetInitiator().ChooseAbilities(effect, *choices)

    def stolen_sai_boost(effect: 'Effect', message: 'Message.WhenCardBecomeBoost') -> None:
        message.would_atk_message.GainPiercing(effect)

    return [
        AbilityFactory.AttachToFaceWhenPutIntoPlay(
            Enemy,
            highest_atk=True,
        ),
        AbilityFactory.UnitAttackGainKeyword(
            "AttachedEnemy",
            piercing=True,
        ),
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.HeroAction,
            stolen_sai_action,
        ).SetCostFunc(CostFunc.Spend(Cost("RR"))),
        AbilityFactory.WhenCardBecomeBoost(
            "This",
            stolen_sai_boost,
            during_attack=True,
        ),
    ]
