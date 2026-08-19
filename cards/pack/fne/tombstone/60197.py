from . import *


def GetAbilities() -> Sequence['Ability']:

    def revealed(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        this = effect.this.CastTo(Minion)
        attachment = Search.EncounterCard(
            effect,
            message.GetToPlayer(),
            include_discard_pile=True,
            finder=CardFinder(card_type=Attachment, canbe_attach_to=this),
        )
        if attachment:
            attachment.AttachTo2(this, effect)

    return [AbilityFactory.WhenThisRevealed(None, revealed)]
