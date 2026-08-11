from cards.pack import *


def BoardMemberSecretThreshold(effect: 'Effect') -> int:
    encounter_sets = effect.world.scene.campaign.encounter_sets
    expert_set_present = any(
        name == "expert" or name.startswith("expert_")
        for name in encounter_sets
    )
    return 3 if expert_set_present or Worlds.IsExpert(effect) else 4


def RecordBoardMemberFlipped(face: 'CardFace', effect: 'Effect') -> None:
    if not Worlds.IsCampaignSelected(effect, "agents_of_shield"):
        return
    front = next(
        (back for back in face.card.back_faces if Environment.IsType(back)),
        None,
    )
    if front:
        CampaignLog.SetStr(
            f"{front.name} Flipped",
            "Yes",
            effect.world,
        )


def BoardMember():

    def chief_medical_officer(effect: 'Effect', message: 'Message.AfterCardPlacedCounter') -> None:
        this = effect.this.CastTo(Environment)
        this.card.Flip(effect)
        aid = this.card.face
        villain = Worlds.FindVillain(effect)
        if villain and Attachment.IsType(aid):
            aid.AttachTo2(villain, effect)
            RecordBoardMemberFlipped(aid, effect)
        if Worlds.FindCardSizeOnField(effect, CardFinder2("BOARD MEMBER", Attachment)) >= 3:
            Worlds.SetGameOver(False, effect)

    return AbilityFactory.IfThereAreAtLeastCounterHere(
        BoardMemberSecretThreshold,
        'secret',
        chief_medical_officer
    )

def IfThereAre3BoardMemberAttachmentsInPlayPlayersLoseTheGame():

    def action(effect: 'Effect', message: 'Message.AfterCardFlip'):
        RecordBoardMemberFlipped(effect.this, effect)
        if Worlds.FindCardSizeOnField(effect, CardFinder2("BOARD MEMBER", Attachment)) >= 3:
            Worlds.SetGameOver(False, effect)

    return AbilityFactory.AfterFlipToThisFace(
        AbilityType.NonKeyword,
        action
    )


def IfThereAre3BoardMemberAttachmentsInPlayAfterThisEntersPlay():

    def action(effect: 'Effect', message: 'Message.AfterCardPutIntoPlay'):
        if Worlds.FindCardSizeOnField(effect, CardFinder2("BOARD MEMBER", Attachment)) >= 3:
            Worlds.SetGameOver(False, effect)

    return Ability(
        AbilityType.NonKeyword,
        Message.AfterCardPutIntoPlay,
        [Condition2.ThisIsTrigger],
        action,
        is_local=True,
    )
