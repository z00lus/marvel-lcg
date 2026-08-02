from . import *


CAMPAIGN_ID = "mutant_genesis"


FUTURE_PAST_CARD_IDS = ["32166", "32167", "32168", "32169", "32170"]

ROLE_UPGRADE_IDS = {
    "Brawler": ["32176", "32177", "32178", "32179", "32180"],
    "Commander": ["32181", "32182", "32183", "32184", "32185"],
    "Defender": ["32186", "32187", "32188", "32189", "32190"],
    "Peacekeeper": ["32191", "32192", "32193", "32194", "32195"],
}

CAMPAIGN_SIDE_SCHEME_IDS = {
    1: "32171a,32171b",
    2: "32172a,32172b",
    3: "32173a,32173b",
    4: "32174a,32174b",
    5: "32175a,32175b",
}

ROLE_UPGRADE_PREREQUISITES = {
    2: "Frightened Police Defeated",
    3: "Enemy of My Enemy Defeated",
    4: "Find the Prisoners Defeated",
    5: "Surprise Attack Defeated",
}


def SetupFuturePastDeck() -> 'Ability':
    def action(effect: 'Effect', message: 'Message.WhenCampaignSetup') -> None:
        from game.operate.campaign_logs import CampaignLog

        encounter_ids = CampaignLog.GetList("Future Past Cards in Encounter Deck", effect)
        removed_ids = CampaignLog.GetList("Future Past Cards removed from campaign", effect)

        encounter_ids = [
            card_id for card_id in FUTURE_PAST_CARD_IDS
            if card_id in encounter_ids and card_id not in removed_ids
        ]
        future_past_ids = [
            card_id for card_id in FUTURE_PAST_CARD_IDS
            if card_id not in encounter_ids and card_id not in removed_ids
        ]

        encounter_deck = Worlds.GetEncounterDeck(effect)
        if encounter_ids:
            CardFactory.GenerateCards(encounter_ids, encounter_deck, effect.world)
            encounter_deck.Shuffle(effect)

        if future_past_ids:
            CardFactory.GenerateCards(future_past_ids, Worlds.AsideDeck(effect), effect.world)

    return AbilityFactoryCampaign.WhenCampaignSetup(action, campaign_id=CAMPAIGN_ID)


def RevealCampaignSideScheme(level: int) -> 'Ability':
    def action(effect: 'Effect', message: 'Message.WhenCampaignSetup') -> None:
        card = CardFactory.GenerateCard(
            CAMPAIGN_SIDE_SCHEME_IDS[level],
            Worlds.AsideDeck(effect),
            effect.world,
        )
        card.face.Reveal(Worlds.GetFirstPlayer(effect), effect)

    return AbilityFactoryCampaign.WhenCampaignSetup(action, campaign_id=CAMPAIGN_ID)


def EachPlayerPutRandomRoleUpgradeIntoPlay(level: int) -> 'Ability':
    def action(effect: 'Effect', message: 'Message.WhenCampaignSetup') -> None:
        from game.operate.campaign_logs import CampaignLog

        prerequisite = ROLE_UPGRADE_PREREQUISITES.get(level)
        if prerequisite and not CampaignLog.GetStr(prerequisite, effect):
            return

        removed_ids = CampaignLog.GetList("Role Upgrades removed from campaign", effect)
        for player in Worlds.GetPlayers(effect):
            role = CampaignLog.GetStrByPlayer("Role", player.player_id, effect)
            available_ids = [
                card_id for card_id in ROLE_UPGRADE_IDS.get(role, [])
                if card_id not in removed_ids
            ]
            if not available_ids:
                continue

            card_id = Rand.RandomChoice(available_ids, effect)
            card = CardFactory.GenerateCard(card_id, None, effect.world)
            card.face.PutIntoPlay(player, effect, under_control=True)

    return AbilityFactoryCampaign.WhenCampaignSetup(action, campaign_id=CAMPAIGN_ID)


def PutJubileeIntoPlay() -> 'Ability':
    def action(effect: 'Effect', message: 'Message.WhenCampaignSetup') -> None:
        from game.operate.campaign_logs import CampaignLog

        if CampaignLog.GetStr("Jubilee", effect):
            card = CardFactory.GenerateCard("32088b", None, effect.world)
            card.face.PutIntoPlay(Worlds.GetFirstPlayer(effect), effect, under_control=True)

    return AbilityFactoryCampaign.WhenCampaignSetup(action, campaign_id=CAMPAIGN_ID)


def EachPlayerShuffleCaptiveAlliesIntoTheirDeck() -> 'Ability':
    def action(effect: 'Effect', message: 'Message.WhenCampaignSetup') -> None:
        from game.operate.campaign_logs import CampaignLog

        removed_ids = CampaignLog.GetList("Allies removed from the campaign", effect)
        for player in Worlds.GetPlayers(effect):
            card_ids = [
                card_id
                for card_id in CampaignLog.GetListByPlayer("Captive Allies", player.player_id, effect)
                if card_id not in removed_ids
            ]
            if card_ids:
                CardFactory.GenerateCards(card_ids, player.player_deck, effect.world)
                player.player_deck.Shuffle(effect)

    return AbilityFactoryCampaign.WhenCampaignSetup(action, campaign_id=CAMPAIGN_ID)


def RemoveCampaignAlliesFromPlayerDecks() -> 'Ability':
    def action(effect: 'Effect', message: 'Message.WhenCampaignSetup') -> None:
        from game.operate.campaign_logs import CampaignLog

        card_ids = CampaignLog.GetList("Allies removed from the campaign", effect)
        if not card_ids:
            return

        for player in Worlds.GetPlayers(effect):
            faces = player.player_deck.FindCards(card_ids=card_ids)
            Faces.RemoveAllFromGame(faces, effect)

    return AbilityFactoryCampaign.WhenCampaignSetup(action, campaign_id=CAMPAIGN_ID)


def ExpertCampaignEachPlayerMayHealAtAccelerationCost() -> 'Ability':
    def action(effect: 'Effect', message: 'Message.WhenCampaignSetup') -> None:
        main_scheme = Worlds.GetAllMainSchemes(effect)[0]
        for player in Worlds.GetPlayers(effect):
            def heal_identity(targets: Sequence['CardFace'], player=player) -> None:
                main_scheme.PlaceAccelerationToken(1, effect)
                effect.this.HealthUnits(targets, "All", effect)

            player.MayChooseOneAbility(
                effect,
                AbilityFactory.ForChoiceAbility(
                    "Place 1 acceleration token on the main scheme to heal their identity to its full hit point value",
                    heal_identity,
                ).SetTarget([player.GetIdentity()], canbe_heal=True),
            )

    return AbilityFactoryCampaign.WhenCampaignSetupExpertOnly(action, campaign_id=CAMPAIGN_ID)


def CampaignSetup(level: int) -> List['Ability']:
    abilities: List['Ability'] = [
        SetupFuturePastDeck(),
        RevealCampaignSideScheme(level),
        EachPlayerPutRandomRoleUpgradeIntoPlay(level),
    ]

    if level >= 3:
        abilities.extend([
            PutJubileeIntoPlay(),
            EachPlayerShuffleCaptiveAlliesIntoTheirDeck(),
            RemoveCampaignAlliesFromPlayerDecks(),
        ])

    if level >= 2:
        abilities.extend([
            AbilityFactoryCampaign.ExpertCampaignSetPlayersHPToTheirRemainingHP(campaign_id=CAMPAIGN_ID),
            ExpertCampaignEachPlayerMayHealAtAccelerationCost(),
        ])

    return abilities
