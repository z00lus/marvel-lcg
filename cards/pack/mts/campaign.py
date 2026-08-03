from . import *


CAMPAIGN_ID = "mad_titans_shadow"

CAMPAIGN_SIDE_SCHEMES = {
    1: "21180a,21180b",
    2: "21182a,21182b",
    3: "21184a,21184b",
    4: "21186a,21186b",
    5: "21189a,21189b",
}


def _log_yes(key: str, effect: 'Effect') -> bool:
    from game.operate.campaign_logs import CampaignLog

    return CampaignLog.GetStrInternal(key, effect) == "Yes"


def _generate_linked_face(card_ids: str, effect: 'Effect') -> 'CardFace':
    return CardFactory.GenerateCard(card_ids, None, effect.world).face


def _flip_to_back(face: 'CardFace', effect: 'Effect') -> 'CardFace':
    face.FlipTo(effect, card_face=face.card.back_faces[0])
    return face.card.face


def _shuffle_encounter_card(card_id: str, effect: 'Effect') -> None:
    face = CardFactory.GenerateCard(card_id, None, effect.world).face
    Faces.ShuffleAllTo([face], "EncounterDeck", effect)


def _shuffle_card_into_each_player_deck(card_id: str, effect: 'Effect') -> None:
    for player in Worlds.GetPlayers(effect):
        CardFactory.GenerateCard(card_id, player.player_deck, effect.world)
        player.player_deck.Shuffle(effect)


def RevealCampaignSideScheme(level: int) -> 'Ability':
    def action(effect: 'Effect', message: 'Message.WhenCampaignSetup') -> None:
        side_scheme = _generate_linked_face(CAMPAIGN_SIDE_SCHEMES[level], effect)
        side_scheme.Reveal(Worlds.GetFirstPlayer(effect), effect)

    return AbilityFactoryCampaign.WhenCampaignSetup(
        action,
        campaign_id=CAMPAIGN_ID,
    )


def AddRecordedCampaignCards(level: int) -> 'Ability':
    def action(effect: 'Effect', message: 'Message.WhenCampaignSetup') -> None:
        first_player = Worlds.GetFirstPlayer(effect)

        if level == 1:
            _shuffle_encounter_card("21181", effect)

        if level in [2, 3] and _log_yes("Security Breach in campaign pool", effect):
            _shuffle_encounter_card("21181", effect)

        if level >= 3 and _log_yes("Shawarma in campaign pool", effect):
            _shuffle_card_into_each_player_deck("21183", effect)

        if level == 3:
            if _log_yes("Cosmo in campaign pool", effect):
                cosmo = _flip_to_back(_generate_linked_face("21180a,21180b", effect), effect)
                cosmo.PutIntoPlay(first_player, effect, under_control=True)

            if _log_yes("Black Swan in campaign pool", effect):
                black_swan = _flip_to_back(_generate_linked_face("21182a,21182b", effect), effect)
                black_swan.PutIntoPlay(first_player, effect)

        if level >= 4:
            _shuffle_encounter_card("21188", effect)

            if _log_yes("System Shock in campaign pool", effect):
                _shuffle_card_into_each_player_deck("21185", effect)

            if _log_yes("The Infinity Stones 1B was completed", effect):
                for player in Worlds.GetPlayers(effect):
                    player.DiscardDeckTopCards(player.player_deck.GetSize() // 2, effect)

        if level == 5:
            if _log_yes("Norn Stone in campaign pool", effect):
                for player in Worlds.GetPlayers(effect):
                    norn_stone = _generate_linked_face("21187a,21187b", effect)
                    norn_stone.PutIntoPlay(player, effect, under_control=True)

            if _log_yes("Odin in campaign pool", effect):
                odin = _flip_to_back(_generate_linked_face("21139a,21139b", effect), effect)
                odin.PutIntoPlay(first_player, effect, under_control=True)

            for card_id in ["21190", "21191", "21192", "21193"]:
                CardFactory.GenerateCard(card_id, effect.world.aside_deck, effect.world)

    return AbilityFactoryCampaign.WhenCampaignSetup(
        action,
        campaign_id=CAMPAIGN_ID,
    )


def ExpertCampaignEachPlayerMayHealAtAccelerationCost() -> 'Ability':
    def action(effect: 'Effect', message: 'Message.WhenCampaignSetup') -> None:
        for player in Worlds.GetPlayers(effect):
            def heal_identity(targets: Sequence['CardFace'], player=player) -> None:
                main_scheme = player.AskChooseFace(
                    Worlds.GetAllMainSchemes(effect),
                    effect,
                    prompt="Choose a main scheme to receive 1 acceleration token",
                )
                if main_scheme:
                    main_scheme.PlaceAccelerationToken(1, effect)
                    effect.this.HealthUnits(targets, "All", effect)

            player.MayChooseOneAbility(
                effect,
                AbilityFactory.ForChoiceAbility(
                    "Place 1 acceleration token on a main scheme to heal their identity to its full hit point value",
                    heal_identity,
                ).SetTarget([player.GetIdentity()], canbe_heal=True),
            )

    return AbilityFactoryCampaign.WhenCampaignSetupExpertOnly(
        action,
        campaign_id=CAMPAIGN_ID,
    )


def DamageIdentitiesForDamagedAvengersTower() -> 'Ability':
    def action(effect: 'Effect', message: 'Message.WhenCampaignSetup') -> None:
        if not _log_yes("Avengers Tower has the Damaged trait", effect):
            return

        for player in Worlds.GetPlayers(effect):
            effect.this.DealDamage([player.GetIdentity()], 3, effect)

    return AbilityFactoryCampaign.WhenCampaignSetup(
        action,
        campaign_id=CAMPAIGN_ID,
    )


def CampaignSetup(level: int) -> List['Ability']:
    abilities: List['Ability'] = [
        RevealCampaignSideScheme(level),
        AddRecordedCampaignCards(level),
    ]

    if level >= 2:
        abilities.extend([
            AbilityFactoryCampaign.ExpertCampaignSetPlayersHPToTheirRemainingHP(
                campaign_id=CAMPAIGN_ID,
            ),
            ExpertCampaignEachPlayerMayHealAtAccelerationCost(),
        ])

    if level == 3:
        abilities.append(DamageIdentitiesForDamagedAvengersTower())

    return abilities
