from . import *

CAMPAIGN_ID = "sinister_motives"

def ChooseCommunityService():
    return AbilityFactoryCampaign.ChooseCardAtRandomAndShuffleIntoEncounterDeck(
        ["27176", "27177", "27178", "27179", "27180"],
        campaign_id=CAMPAIGN_ID,
    )

def FollowSetupInstructionOfReputationTrack() -> 'Ability':
    def action(effect: 'Effect', message: 'Message.WhenCampaignSetup'):
        this = effect.this
        value = CampaignLog.GetInt("Reputation Track", effect)
        if value >= 1:
            for player in Worlds.GetPlayers(effect):
                player_id = player.player_id
                card_id = CampaignLog.GetStrByPlayer("S.H.I.E.L.D. Tech: Reputation Track Reward", player_id, effect)
                if card_id:
                    card = CardFactory.GenerateCard(card_id, player.discard_pile, effect.world)
                    # Faces.ShuffleAllTo([card.face], player.player_deck, effect)
                    card.face.PutIntoPlay(player, effect)
                    if value >= 13:
                        card.face.FlipTo(effect, trait="ENHANCED")
        if value >= 5:
            effect.world.rule.additional_resolve_mulligans.Set(True)
        if value >= 9:
            for player in Worlds.GetPlayers(effect):
                player_id = player.player_id
                card_ids = CampaignLog.GetListByPlayer("Aspect Advantage: Reputation Track Reward", player_id, effect)
                cards = CardFactory.GenerateCards(card_ids, player.discard_pile, effect.world)
                Faces.ShuffleAllTo([card.face for card in cards], player.player_deck, effect)
        # if value >= 13:
        #     pass
        if value >= 17:
            def action(player: 'Player'):
                player_id = player.player_id
                card_id = CampaignLog.GetStrByPlayer("Planning Ahead: Reputation Track Reward", player_id, effect)
                face = Search.PlayerCard(
                    effect,
                    player,
                    include_player_deck=True,
                    include_discard_pile=True,
                    card_ids=[card_id],
                )
                if face:
                    Faces.AddToHand([face], player, effect)
            Players.ForEachPlayer(effect, action)
        if value >= 21:
            def action(player: 'Player'):
                def action2(targets: Sequence['CardFace']):
                    card = CardFactory.GenerateCard("01092", player.discard_pile, effect.world)
                    card.face.PutIntoPlay(player, effect, under_control=True)
                player.MayChooseOneAbility(
                    effect,
                    AbilityFactory.ForChoiceAbility(
                        "Search their collection for a Helicarrier support and put it into play under their control",
                        action2
                    )
                )
            Players.ForEachPlayer(effect, action)
        if value >= 25:
            def action(player: 'Player'):
                def action2(targets: Sequence['CardFace']):
                    card = CardFactory.GenerateCard("27191", player.discard_pile, effect.world)
                    card.face.PutIntoPlay(player, effect, under_control=True)
                player.MayChooseOneAbility(
                    effect,
                    AbilityFactory.ForChoiceAbility(
                        "search their collection for a Symbiote Suit upgrade and put it into play under their control.",
                        action2
                    )
                )
            Players.ForEachPlayer(effect, action)

        if value >= 1:
            card_ids = CampaignLog.GetList("Osborn Tech: Reputation Track Penalty", effect)
            cards = CardFactory.GenerateCards(card_ids, None, effect.world)
            Faces.ShuffleAllTo([x.face for x in cards], "EncounterDeck", effect)
        if value >= 5:
            this.PlaceThreatOnSchemes("MainScheme", "1*", effect)
        if value >= 9:
            def action(player: 'Player'):
                face = Search.EncounterCard(
                    effect,
                    player,
                    include_discard_pile=True,
                    card_type=Minion
                )
                def deal():
                    player.DealEncounterCards(1, effect)
                if face:
                    if not face.PutIntoPlay(player, effect):
                        deal()
                else:
                    deal()
            Players.ForEachPlayer(effect, action)
        if value >= 17:
            face = Search.EncounterCard(
                effect,
                "FirstPlayer",
                include_discard_pile=True,
                card_type=SchemeSide2,
                is_scenario_specific=True,
            )
            if face:
                face.Reveal("FirstPlayer", effect)
                this.PlaceThreatOnSchemes([face], "1*", effect)
        if value >= 25:
            def action(player: 'Player'):
                player.DealEncounterCards(1, effect)
            Players.ForEachPlayer(effect, action)

    return AbilityFactoryCampaign.WhenCampaignSetup(action, campaign_id=CAMPAIGN_ID)

def CampaignSetup(level: int, *,
                campaign: Callable[[Effect, Message.WhenCampaignSetup], None]|None=None,
                campaign_expert: Callable[[Effect, Message.WhenCampaignSetup], None]|None=None) -> List['Ability']:

    abilities: List['Ability'] = []
    if level >= 3 and level != 5:
        abilities.append(
            AbilityFactoryCampaign.PutCardIntoPlay(
                "27190",
                under_control="FirstPlayer",
                campaign_id=CAMPAIGN_ID,
            )
        )

    if level >= 1:
        abilities.append(
            AbilityFactoryCampaign.PutCardIntoPlay(
                "27174a,27174b",
                campaign_id=CAMPAIGN_ID,
            )
        )
        abilities.append(
            AbilityFactoryCampaign.ShuffleCardIntoDeck(
                "27175",
                "EncounterDeck",
                campaign_id=CAMPAIGN_ID,
            )
        )

    if level >= 3 and level != 5:
        abilities.append(
            AbilityFactoryCampaign.ShuffleCardIntoDeck(
                "27181",
                "EncounterDeck",
                campaign_id=CAMPAIGN_ID,
            )
        )

    if level >= 1 and level != 5:
        abilities.append(
            ChooseCommunityService()
        )

    if level >= 2:
        abilities.append(
            FollowSetupInstructionOfReputationTrack(),
        )

    if campaign:
        abilities.append(
            AbilityFactoryCampaign.WhenCampaignSetup(
                campaign,
                campaign_id=CAMPAIGN_ID,
            ),
        )

    # Expert
    if level >= 2:
        abilities.append(
            AbilityFactoryCampaign.ExpertCampaignSetPlayersHPToTheirRemainingHP(campaign_id=CAMPAIGN_ID),
        )
        value = {
            2: 1,
            3: 2,
            4: 2,
            5: 3
        }[level]
        abilities.append(
            AbilityFactoryCampaign.ExpertCampaignEachPlayerMayDealFacedownEncounterCardYpHealHP(
                value,
                campaign_id=CAMPAIGN_ID,
            ),
        )

    if campaign_expert:
        abilities.append(
            AbilityFactoryCampaign.WhenCampaignSetupExpertOnly(
                campaign_expert,
                campaign_id=CAMPAIGN_ID,
            ),
        )

    return abilities
