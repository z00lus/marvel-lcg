from . import *


CAMPAIGN_ID = "galaxys_most_wanted"

MARKET_CARD_IDS = [str(card_id) for card_id in range(16150, 16178)]
CHALLENGE_SIDE_SCHEMES = {
    1: "16178a,16178b",
    2: "16179a,16179b",
    3: "16180a,16180b",
    4: "16181a,16181b",
    5: "16182a,16182b",
}
HEADHUNTER_CARDS = ["16183", "16184", "16185", "16186", "16187"]
GALACTIC_ARTIFACT_SIDE_SCHEMES = ["16127", "16128", "16129", "16130"]


def _campaign_list(key: str, effect: 'Effect') -> List[str]:
    from game.operate.campaign_logs import CampaignLog

    return CampaignLog.GetListInternal(key, effect)


def _campaign_int(key: str, effect: 'Effect') -> int:
    from game.operate.campaign_logs import CampaignLog

    return CampaignLog.GetIntInternal(key, effect)


def _campaign_str(key: str, effect: 'Effect') -> str:
    from game.operate.campaign_logs import CampaignLog

    return CampaignLog.GetStrInternal(key, effect)


def _generate_challenge_side_scheme(level: int, effect: 'Effect') -> 'CardFace':
    card = CardFactory.GenerateCard(
        CHALLENGE_SIDE_SCHEMES[level],
        None,
        effect.world,
    )
    if Worlds.IsExpert(effect):
        card.face.FlipTo(effect, card_face=card.face.card.back_faces[0])
    return card.face


def RevealChallengeSideScheme(level: int) -> 'Ability':
    def action(effect: 'Effect', message: 'Message.WhenCampaignSetup') -> None:
        if level == 5 and _campaign_str("Reveal Kree Supremacy", effect) != "Yes":
            return

        side_scheme = _generate_challenge_side_scheme(level, effect)
        side_scheme.Reveal(Worlds.GetFirstPlayer(effect), effect)

    return AbilityFactoryCampaign.WhenCampaignSetup(
        action,
        campaign_id=CAMPAIGN_ID,
    )


def AddMarketCardsToPlayerDecks(level: int) -> 'Ability':
    def action(effect: 'Effect', message: 'Message.WhenGameBeginSetup') -> None:
        if level == 1:
            return

        for player in Worlds.GetPlayers(effect):
            card_ids = [
                card_id
                for card_id in _campaign_list(
                    f"Player {player.player_id + 1} Market Cards",
                    effect,
                )
                if card_id in MARKET_CARD_IDS
            ]
            if card_ids:
                CardFactory.GenerateCards(card_ids, player.player_deck, effect.world)
                player.player_deck.Shuffle(effect)

    return AbilityFactory.WhenGameBeginSetup(
        action,
        conditions=[
            lambda effect, message:
                Worlds.IsCampaignSelected(effect, CAMPAIGN_ID),
        ],
    )


def AddProgressiveHeadhunterCards(level: int) -> 'Ability':
    def action(effect: 'Effect', message: 'Message.WhenCampaignSetup') -> None:
        defeated_count = len(_campaign_list("Headhunter Defeated", effect))
        card_ids = [HEADHUNTER_CARDS[0]]
        card_ids.extend(HEADHUNTER_CARDS[1:min(defeated_count + 1, level)])

        encounter_deck = Worlds.GetEncounterDeck(effect)
        CardFactory.GenerateCards(card_ids, encounter_deck, effect.world)
        encounter_deck.Shuffle(effect)

    return AbilityFactoryCampaign.WhenCampaignSetup(
        action,
        campaign_id=CAMPAIGN_ID,
    )


def RemoveCardsRecordedInTheCollection() -> 'Ability':
    def action(effect: 'Effect', message: 'Message.WhenCampaignSetup') -> None:
        for player in Worlds.GetPlayers(effect):
            card_ids = _campaign_list(
                f"Player {player.player_id + 1} Cards in The Collection",
                effect,
            )
            removed_from_deck = False

            for card_id in card_ids:
                face = player.hand_cards.FindCard(card_ids=[card_id])
                if not face:
                    face = player.discard_pile.FindCard(card_ids=[card_id])
                if not face:
                    face = player.player_deck.FindCard(card_ids=[card_id])
                    removed_from_deck = removed_from_deck or face is not None
                if face:
                    Faces.RemoveAllFromGame([face], effect)

            if removed_from_deck:
                player.player_deck.Shuffle(effect)

    return AbilityFactoryCampaign.WhenCampaignSetup(
        action,
        campaign_id=CAMPAIGN_ID,
    )


def AddRecordedGalacticArtifactsToNebula() -> 'Ability':
    def action(effect: 'Effect', message: 'Message.WhenCampaignSetup') -> None:
        card_ids = [
            card_id
            for card_id in _campaign_list(
                "Galactic Artifacts Side Schemes in the Victory Display",
                effect,
            )
            if card_id in GALACTIC_ARTIFACT_SIDE_SCHEMES
        ]
        if not card_ids:
            return

        encounter_deck = Worlds.GetEncounterDeck(effect)
        CardFactory.GenerateCards(card_ids, encounter_deck, effect.world)
        encounter_deck.Shuffle(effect)

        villain = Worlds.FindVillain(effect)
        first_player = Worlds.GetFirstPlayer(effect)
        nebulas_ship = Worlds.FindCardOnField(
            effect,
            name="Nebula's Ship",
            card_type=Environment,
        )

        for card_id in card_ids:
            if card_id == "16127" and nebulas_ship:
                Faces.PlaceCountersOn([nebulas_ship], 1, "evasion", effect)
            elif card_id == "16128":
                first_player.DealEncounterCards(1, effect)
            elif card_id == "16129" and villain:
                Faces.GiveFacedownBoostCards([villain], 1, effect)
            elif card_id == "16130" and villain:
                Faces.GiveStatus([villain], "Tough", effect)

    return AbilityFactoryCampaign.WhenCampaignSetup(
        action,
        campaign_id=CAMPAIGN_ID,
    )


def _normalize_player_name(value: str) -> str:
    return "".join(character for character in value.casefold() if character.isalnum())


def _find_power_stone_player(effect: 'Effect') -> 'Player|None':
    recorded = _normalize_player_name(_campaign_str("Power Stone Control", effect))
    if not recorded:
        return None

    for player in Worlds.GetPlayers(effect):
        identity = player.GetIdentity()
        candidates = [
            f"Player {player.player_id + 1}",
            f"P{player.player_id + 1}",
            str(player.player_id + 1),
            identity.GetHeroFace().name,
            identity.GetAlterEgoFace().name,
        ]
        if recorded in {_normalize_player_name(value) for value in candidates}:
            return player
    return None


def ApplyRonanCampaignSetup() -> 'Ability':
    def action(effect: 'Effect', message: 'Message.WhenCampaignSetup') -> None:
        encounter_deck = Worlds.GetEncounterDeck(effect)
        discard_pile = Worlds.GetEncounterDiscardPile(effect)

        power_stone_player = _find_power_stone_player(effect)
        if power_stone_player:
            accused = encounter_deck.FindCard(card_ids=["16116"])
            if not accused:
                accused = discard_pile.FindCard(card_ids=["16116"])
            if accused:
                power_stone_player.DealEncounterCard(accused, effect)

        pincer_maneuver = encounter_deck.FindCard(card_ids=["16112"])
        if not pincer_maneuver:
            pincer_maneuver = discard_pile.FindCard(card_ids=["16112"])
        if pincer_maneuver:
            pincer_maneuver.Reveal(Worlds.GetFirstPlayer(effect), effect)
            additional_threat = max(0, 3 - _campaign_int("Evasion Counters", effect))
            if additional_threat:
                effect.this.PlaceThreatOnSchemes(
                    [pincer_maneuver],
                    additional_threat,
                    effect,
                )

    return AbilityFactoryCampaign.WhenCampaignSetup(
        action,
        campaign_id=CAMPAIGN_ID,
    )


def ExpertCampaignEachPlayerMaySpendUnitToHeal() -> 'Ability':
    def action(effect: 'Effect', message: 'Message.WhenCampaignSetup') -> None:
        from game.operate.campaign_logs import CampaignLog

        for player in Worlds.GetPlayers(effect):
            key = f"Player {player.player_id + 1} Unspent Units"
            unspent_units = _campaign_int(key, effect)

            def heal_identity(
                targets: Sequence['CardFace'],
                player=player,
                key=key,
                unspent_units=unspent_units,
            ) -> None:
                CampaignLog.SetStr(key, str(unspent_units - 1), effect.world)
                effect.this.HealthUnits(targets, "All", effect)

            player.MayChooseOneAbility(
                effect,
                AbilityFactory.ForChoiceAbility(
                    "Spend 1 unit to heal their identity to its printed hit point value",
                    heal_identity,
                    condition=unspent_units > 0,
                ).SetTarget([player.GetIdentity()], canbe_heal=True),
            )

    return AbilityFactoryCampaign.WhenCampaignSetupExpertOnly(
        action,
        campaign_id=CAMPAIGN_ID,
    )


def ExpertCampaignPutMinionIntoPlayForEachPlayer() -> 'Ability':
    def action(effect: 'Effect', message: 'Message.WhenCampaignSetup') -> None:
        for player in Worlds.GetPlayers(effect):
            minion = Worlds.DiscardEncounterCardsUntil(effect, card_type=Minion)
            if minion:
                minion.PutIntoPlay(player, effect)

    return AbilityFactoryCampaign.WhenCampaignSetupExpertOnly(
        action,
        campaign_id=CAMPAIGN_ID,
    )


def ExpertCampaignRevealAttachmentForEachPlayer() -> 'Ability':
    def action(effect: 'Effect', message: 'Message.WhenCampaignSetup') -> None:
        for player in Worlds.GetPlayers(effect):
            attachment = Worlds.DiscardEncounterCardsUntil(
                effect,
                card_type=Attachment,
            )
            if attachment:
                attachment.Reveal(player, effect)

    return AbilityFactoryCampaign.WhenCampaignSetupExpertOnly(
        action,
        campaign_id=CAMPAIGN_ID,
    )


def ExpertCampaignAttachTechniqueToNebula() -> 'Ability':
    def action(effect: 'Effect', message: 'Message.WhenCampaignSetup') -> None:
        technique = Worlds.DiscardEncounterCardsUntil(
            effect,
            card_type=Attachment,
            trait="TECHNIQUE",
        )
        villain = Worlds.FindVillain(effect)
        if technique and villain:
            technique.AttachTo2(villain, effect)

    return AbilityFactoryCampaign.WhenCampaignSetupExpertOnly(
        action,
        campaign_id=CAMPAIGN_ID,
    )


def ExpertCampaignPlaceAdditionalThreatOnRonanMainScheme() -> 'Ability':
    def action(effect: 'Effect', message: 'Message.WhenCampaignSetup') -> None:
        main_scheme = Worlds.GetMainSchemes(effect)[0]
        effect.this.PlaceThreatOnSchemes([main_scheme], "1*", effect)

    return AbilityFactoryCampaign.WhenCampaignSetupExpertOnly(
        action,
        campaign_id=CAMPAIGN_ID,
    )


def ExpertCampaignAddHandCardToTheCollectionAfterSetup() -> 'Ability':
    def action(effect: 'Effect', message: 'Message.WhenGameWouldBegin') -> None:
        from cards.pack.gmw.collector_1 import PutCardIntoTheCollection

        for player in Worlds.GetPlayers(effect):
            card = player.AskChooseFace(
                player.hand_cards.Get(),
                effect,
                prompt="Choose 1 card from your hand to put faceup into The Collection",
            )
            if card:
                PutCardIntoTheCollection([card], effect)

    return AbilityFactory.WhenGameWouldBegin(
        action,
        conditions=[
            lambda effect, message:
                Worlds.IsCampaignSelected(effect, CAMPAIGN_ID) and
                Worlds.IsExpert(effect),
        ],
    )


def CampaignSetup(level: int) -> List['Ability']:
    abilities: List['Ability'] = [
        AddMarketCardsToPlayerDecks(level),
        RevealChallengeSideScheme(level),
    ]

    if level == 3:
        abilities.append(RemoveCardsRecordedInTheCollection())
    elif level == 4:
        abilities.append(AddRecordedGalacticArtifactsToNebula())
    elif level == 5:
        abilities.append(ApplyRonanCampaignSetup())

    abilities.append(AddProgressiveHeadhunterCards(level))

    if level == 1:
        abilities.append(ExpertCampaignPutMinionIntoPlayForEachPlayer())
    else:
        abilities.extend([
            AbilityFactoryCampaign.CampaignSetPlayersHPToTheirRemainingHP(
                campaign_id=CAMPAIGN_ID,
            ),
            ExpertCampaignEachPlayerMaySpendUnitToHeal(),
        ])

        if level == 3:
            abilities.append(ExpertCampaignRevealAttachmentForEachPlayer())
        elif level == 4:
            abilities.append(ExpertCampaignAttachTechniqueToNebula())
        elif level == 5:
            abilities.append(ExpertCampaignPlaceAdditionalThreatOnRonanMainScheme())

    return abilities
