from . import *


def GetAbilities() -> Sequence['Ability']:

    def revealed(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        attachment = Worlds.DiscardEncounterCardsUntil(
            effect,
            card_type=Attachment,
            trait="VEHICLE",
        )
        if not attachment:
            return

        player = message.GetToPlayer()
        identity = player.GetIdentity()
        has_vehicle = bool(CardFinder(
            trait="VEHICLE",
            card_type=Attachment,
        ).Checks(identity.GetAttachedAttachments()))
        if not has_vehicle and player.AskSpendResources(
            Cost("3", same_type=True),
            effect,
        ):
            attachment.AttachTo2(identity, effect)
        else:
            attachment.Reveal(player, effect)

    return [AbilityFactory.WhenThisRevealed(None, revealed)]
