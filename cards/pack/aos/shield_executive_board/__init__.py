from cards.pack import *

def BoardMember():

    def chief_medical_officer(effect: 'Effect', message: 'Message.AfterCardPlacedCounter') -> None:
        this = effect.this.CastTo(Environment)
        this.card.Flip(effect)
        aid = this.card.face
        villain = Worlds.FindVillain(effect)
        if villain and Attachment.IsType(aid):
            aid.AttachTo2(villain, effect)
        if Worlds.FindCardSizeOnField(effect, CardFinder2("BOARD MEMBER", Attachment)) >= 3:
            Worlds.SetGameOver(False, effect)

    return AbilityFactory.IfThereAreAtLeastCounterHere(
        lambda effect: 3 if Worlds.IsExpert(effect) else 4,
        'secret',
        chief_medical_officer
    )

def IfThereAre3BoardMemberAttachmentsInPlayPlayersLoseTheGame():

    def action(effect: 'Effect', message: 'Message.AfterCardFlip'):
        if Worlds.FindCardSizeOnField(effect, CardFinder2("BOARD MEMBER", Attachment)) >= 3:
            Worlds.SetGameOver(False, effect)

    return AbilityFactory.AfterFlipToThisFace(
        AbilityType.NonKeyword,
        action
    )
