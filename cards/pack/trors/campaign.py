from . import *

CAMPAIGN_ID = "rise_of_red_skull"

def ShuffleEachExperimentalAttachmentIntoTheEncounterDeck() -> 'Ability':
    from game.operate.worlds import Worlds
    from game.operate.campaign_logs import CampaignLog
    from game.card.factory import CardFactory
    def action(effect: 'Effect', message: 'Message.WhenCampaignSetup'):
        card_ids = CampaignLog.GetList("Experimental Weapons added to encounter deck", effect)
        encounter_deck = Worlds.GetEncounterDeck(effect)
        CardFactory.GenerateCards(card_ids, encounter_deck, effect.world)
        encounter_deck.Shuffle(effect)

    return AbilityFactoryCampaign.WhenCampaignSetup(
        action,
        campaign_id=CAMPAIGN_ID,
    )

def EachPlayerSearchTheirDeckForSetupKeyword() -> 'Ability':
    from game.operate.worlds import Worlds
    from game.operate.campaign_logs import CampaignLog
    from game.card.factory import CardFactory
    def action(effect: 'Effect', message: 'Message.WhenCampaignSetup'):
        for player in Worlds.GetPlayers(effect):
            player_id = player.player_id
            card_id = CampaignLog.GetStrByPlayer("Tech Upgrade", player_id, effect)
            if card_id:
                card = CardFactory.GenerateCard(card_id, player.player_deck, effect.world)
                card.face.PutIntoPlay(player, effect)

        for player in Worlds.GetPlayers(effect):
            player_id = player.player_id
            card_id = CampaignLog.GetStrByPlayer("Basic Upgrade", player_id, effect)
            if card_id:
                card = CardFactory.GenerateCard(card_id, player.player_deck, effect.world)
                card.face.PutIntoPlay(player, effect)

    return AbilityFactoryCampaign.WhenCampaignSetup(
        action,
        campaign_id=CAMPAIGN_ID,
    )

def EachPlayerAddRescuedAlliesToTheirDeck() -> 'Ability':
    from game.operate.worlds import Worlds
    from game.operate.campaign_logs import CampaignLog
    from game.card.factory import CardFactory
    def action(effect: 'Effect', message: 'Message.WhenCampaignSetup'):
        for player in Worlds.GetPlayers(effect):
            player_id = player.player_id
            card_ids = CampaignLog.GetListByPlayer("Rescued Allies", player_id, effect)
            if card_ids:
                CardFactory.GenerateCards(card_ids, player.player_deck, effect.world)
                player.player_deck.Shuffle(effect)

    return AbilityFactoryCampaign.WhenCampaignSetup(
        action,
        campaign_id=CAMPAIGN_ID,
    )

def EachPlayerMayAddRandomObligationToHealHP() -> 'Ability':
    return AbilityFactoryCampaign.ExpertCampaignAddRandomObligationFromExpertCampaignToHealHP(
        ["04163", "04164", "04165", "04166"],
        campaign_id=CAMPAIGN_ID,
    )


def CampaignSetup(level: int, *,
                campaigns: List[Callable[[Effect, Message.WhenCampaignSetup], None]]=[],
                campaigns_expert: List[Callable[[Effect, Message.WhenCampaignSetup], None]]=[]) -> List['Ability']:

    abilities: List[Ability] = []

    if level >= 2:
        abilities.append(
            EachPlayerSearchTheirDeckForSetupKeyword(),
        )
        abilities.append(
            ShuffleEachExperimentalAttachmentIntoTheEncounterDeck(),
        )

    if level >= 4:
        abilities.append(
            EachPlayerAddRescuedAlliesToTheirDeck(),
        )

    for campaign in campaigns:
        abilities.append(
            AbilityFactoryCampaign.WhenCampaignSetup(campaign, campaign_id=CAMPAIGN_ID),
        )

    if level >= 2:
        abilities.append(
            AbilityFactoryCampaign.CampaignSetPlayersHPToTheirRemainingHP(campaign_id=CAMPAIGN_ID),
        )
        abilities.append(
            EachPlayerMayAddRandomObligationToHealHP()
        )

    for campaign in campaigns_expert:
        abilities.append(
            AbilityFactoryCampaign.WhenCampaignSetupExpertOnly(campaign, campaign_id=CAMPAIGN_ID),
        )

    return abilities
