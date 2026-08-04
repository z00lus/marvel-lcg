from . import *

# Disarming Defense

def GetAbilities() -> Sequence['Ability']:

    def disarming_defense(effect: 'Effect', message: 'Message.WhenUnitWouldDefend') -> None:
        this = effect.this.CastTo(Event)
        Unused(this)

        initiator = effect.GetInitiator()
        message.GainDEFForThisAttack(+2, effect)

        def discard_attachment() -> None:
            attachments = CardFinder(
                card_type=Attachment,
                with_texts=["Hero Action", "Hero Response"],
                canbe_discard=True,
            ).Checks(message.attacker.GetAttachedAttachments(), effect)
            if attachments:
                initiator.ChooseAbilities(
                    effect,
                    AbilityFactory.ForChoiceAbility(
                        "Discard an action or response attachment",
                        lambda targets: Faces.DiscardAll(targets, effect),
                    ).SetTarget(attachments),
                )

        message.IfYouTakeNoDamage(discard_attachment)


    return [
        AbilityFactory.WhenUnitDefendAgainstAttack(
            AbilityType.Interrupt,
            "YourHero",
            disarming_defense,
        ).SetPlay().SetLabel('defense'),
    ]
