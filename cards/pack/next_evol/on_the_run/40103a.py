from . import *
from cards.pack.next_evol.campaign import *

# Gotta Get Away

def GetAbilities() -> Sequence['Ability']:

    def gotta_get_away(effect: 'Effect', message: 'Message.WhenCardSetup') -> None:
        this = effect.this.CastTo(MainScheme)
        Unused(this)

        villains = Worlds.AsideDeck(effect).FindCards(card_type=Villain, trait="MARAUDER")
        all_villains = villains[:]
        if Worlds.IsCampaignSelected(effect, CAMPAIGN_ID):
            from game.operate.campaign_logs import CampaignLog

            defeated_ids = {
                card_id[:5]
                for card_id in CampaignLog.GetListInternal("Marauders Defeated", effect)
            }
            villains = [
                villain for villain in villains
                if villain.paper.card_id[:5] not in defeated_ids
            ]

        if not villains:
            villains = all_villains
        villain = Rand.RandomChoice(villains, effect)
        villain.PutIntoPlay("FirstPlayer", effect)

        minion = Worlds.GetEncounterDeck(effect).FindCard(name=villain.name, card_type=Minion)
        if minion:
            Faces.RemoveAllFromGame([minion], effect)

        face = Worlds.AsideDeck(effect).FindCard(name="Hope's Captor", card_type=Attachment)
        if face:
            face.AttachTo2(villain, effect)

    return [
        *CampaignSetup(2),
        AbilityFactory.WhenCardSetup(
            "This",
            gotta_get_away
        ),
    ]
