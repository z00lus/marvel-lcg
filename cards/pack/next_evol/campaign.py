from . import *


CAMPAIGN_ID = "next_evolution"

PLAYER_SIDE_SCHEMES = {
    "40190a": ("40190a,40190b", "40199", "40190b"),
    "40191a": ("40191a,40191b", "40201", "40191b"),
    "40192a": ("40192a,40192b", "40203", "40192b"),
    "40193a": ("40193a,40193b", "40200", "40193b"),
    "40194a": ("40194a,40194b", "40198", "40194b"),
    "40195a": ("40195a,40195b", "40202", "40195b"),
}

CAMPAIGN_ENVIRONMENT_IDS = [value[2] for value in PLAYER_SIDE_SCHEMES.values()]


def _selected_player_side_schemes(level: int, effect: 'Effect') -> List[str]:
    from game.operate.campaign_logs import CampaignLog

    selected: List[str] = []
    for scenario in range(1, level + 1):
        card_id = CampaignLog.GetStrInternal(
            f"Scenario {scenario} Player Side Scheme",
            effect,
        )
        if card_id in PLAYER_SIDE_SCHEMES and card_id not in selected:
            selected.append(card_id)
    return selected


def _earned_environment_ids(effect: 'Effect') -> List[str]:
    from game.operate.campaign_logs import CampaignLog

    logged = CampaignLog.GetListInternal("Campaign Environments Earned", effect)
    return [card_id for card_id in CAMPAIGN_ENVIRONMENT_IDS if card_id in logged]


def PutEarnedCampaignEnvironmentsIntoPlay() -> 'Ability':
    def action(effect: 'Effect', message: 'Message.WhenCampaignSetup') -> None:
        first_player = Worlds.GetFirstPlayer(effect)
        for card_id in _earned_environment_ids(effect):
            card = CardFactory.GenerateCard(card_id, None, effect.world)
            card.face.PutIntoPlay(first_player, effect)

    return AbilityFactoryCampaign.WhenCampaignSetup(action, campaign_id=CAMPAIGN_ID)


def SetupCampaignPlayerSideScheme(level: int) -> 'Ability':
    def action(effect: 'Effect', message: 'Message.WhenCampaignSetup') -> None:
        from game.operate.campaign_logs import CampaignLog

        selected = _selected_player_side_schemes(level, effect)
        current_id = CampaignLog.GetStrInternal(
            f"Scenario {level} Player Side Scheme",
            effect,
        )
        previously_selected = _selected_player_side_schemes(level - 1, effect)
        if current_id in PLAYER_SIDE_SCHEMES and current_id not in previously_selected:
            card = CardFactory.GenerateCard(
                PLAYER_SIDE_SCHEMES[current_id][0],
                None,
                effect.world,
            )
            card.face.PutIntoPlay(Worlds.GetFirstPlayer(effect), effect)

        encounter_faces = [
            CardFactory.GenerateCard(
                PLAYER_SIDE_SCHEMES[card_id][1],
                None,
                effect.world,
            ).face
            for card_id in selected
        ]
        if encounter_faces:
            Faces.ShuffleAllTo(encounter_faces, "EncounterDeck", effect)

    return AbilityFactoryCampaign.WhenCampaignSetup(action, campaign_id=CAMPAIGN_ID)


def EachPlayerSearchForCardForSavedMorlock() -> 'Ability':
    def action(effect: 'Effect', message: 'Message.WhenCampaignSetup') -> None:
        from game.operate.campaign_logs import CampaignLog

        first_player = Worlds.GetFirstPlayer(effect)
        for _ in range(CampaignLog.GetIntInternal("Morlocks Saved", effect)):
            def choose_player(targets: Sequence['CardFace']) -> None:
                player = targets[0].GetControlByPlayer()
                face = Search.PlayerCard(
                    effect,
                    player,
                    include_player_deck=True,
                )
                if face:
                    player.GainCard(face, effect)

            first_player.ChooseAbilities(
                effect,
                AbilityFactory.ForChoiceAbility(
                    "Choose a player to search their deck for 1 card and add it to their hand",
                    choose_player,
                ).SetTarget("Players"),
            )

    return AbilityFactoryCampaign.WhenCampaignSetup(action, campaign_id=CAMPAIGN_ID)


def GiveEachEnemyToughForCampaignEnvironment() -> 'Ability':
    def action(effect: 'Effect', message: 'Message.WhenCampaignSetup') -> None:
        if _earned_environment_ids(effect):
            Faces.GiveStatus(Worlds.GetOnFieldEnemies(effect), "Tough", effect)

    return AbilityFactoryCampaign.WhenCampaignSetup(action, campaign_id=CAMPAIGN_ID)


def PlaceMomentumCountersOnJuggernaut() -> 'Ability':
    def action(effect: 'Effect', message: 'Message.WhenCampaignSetup') -> None:
        villain = Worlds.FindCardOnField(effect, name="Juggernaut", card_type=Villain)
        if villain:
            Faces.PlaceCountersOn(
                [villain],
                len(_earned_environment_ids(effect)),
                'momentum',
                effect,
            )

    return AbilityFactoryCampaign.WhenCampaignSetup(action, campaign_id=CAMPAIGN_ID)


def DealBlackTomAndCreepingWillows() -> 'Ability':
    def action(effect: 'Effect', message: 'Message.WhenCampaignSetup') -> None:
        players = Worlds.GetPlayers(effect)
        encounter_deck = Worlds.GetEncounterDeck(effect)
        black_tom = encounter_deck.FindCard(name="Black Tom Cassidy", card_type=Minion)
        willows = encounter_deck.FindCards(name="Creeping Willow", card_type=Minion)
        if not black_tom:
            black_tom = CardFactory.GenerateCard("40132", None, effect.world).face
        while len(willows) < len(players):
            willows.append(CardFactory.GenerateCard("40133", None, effect.world).face)
        faces = [black_tom, *willows[:len(players)]]
        Rand.Shuffle(faces, effect)

        for player in players:
            player.DealEncounterCard(faces.pop(), effect)

        if faces:
            Faces.ShuffleAllTo(faces, "EncounterDeck", effect)

    return AbilityFactoryCampaign.WhenCampaignSetup(action, campaign_id=CAMPAIGN_ID)


def RevealTeleportedAwayWithCampaignThreat() -> 'Ability':
    def action(effect: 'Effect', message: 'Message.WhenCampaignSetup') -> None:
        scheme = SetupCards.Reveal(
            effect,
            name="Teleported Away",
            card_type=EncounterSideScheme,
        )
        if scheme:
            extra_threat = len(_earned_environment_ids(effect)) * len(Worlds.GetPlayers(effect))
            effect.this.PlaceThreatOnSchemes([scheme], extra_threat, effect)

    return AbilityFactoryCampaign.WhenCampaignSetup(action, campaign_id=CAMPAIGN_ID)


def ApplyPreviousHopeDamage(previous_scenario: int, destination_key: str) -> 'Ability':
    def action(effect: 'Effect', message: 'Message.WhenCampaignSetup') -> None:
        from game.operate.campaign_logs import CampaignLog

        damage = CampaignLog.GetIntInternal(
            f"Scenario {previous_scenario} Hope Summers Damage",
            effect,
        )
        if damage <= 0:
            return

        destination = CampaignLog.GetStrInternal(destination_key, effect)
        if destination == "Hope Summers":
            hope = Worlds.FindCardOnField(effect, name="Hope Summers", card_type=Ally)
            if hope:
                hope.TakeDamage(effect.this, damage, effect)
        elif destination:
            scheme = Worlds.FindCardOnField(
                effect,
                name=destination,
                card_type=EncounterSideScheme,
            )
            if scheme:
                effect.this.PlaceThreatOnSchemes([scheme], damage, effect)

    return AbilityFactoryCampaign.WhenCampaignSetup(action, campaign_id=CAMPAIGN_ID)


def AddThreatToStryfesGrasp() -> 'Ability':
    def action(effect: 'Effect', message: 'Message.WhenCampaignSetup') -> None:
        scheme = Worlds.FindCardOnField(
            effect,
            name="Stryfe's Grasp",
            card_type=EncounterSideScheme,
        )
        if scheme:
            extra_threat = len(_earned_environment_ids(effect)) * len(Worlds.GetPlayers(effect))
            effect.this.PlaceThreatOnSchemes([scheme], extra_threat, effect)

    return AbilityFactoryCampaign.WhenCampaignSetup(action, campaign_id=CAMPAIGN_ID)


def EachPlayerRevealMinionOrPsionicAttachment() -> 'Ability':
    def action(effect: 'Effect', message: 'Message.WhenCampaignSetup') -> None:
        encounter_deck = Worlds.GetEncounterDeck(effect)
        for player in Worlds.GetPlayers(effect):
            while True:
                face = Worlds.DiscardEncounterTopCard(effect)
                if not face:
                    break
                if Minion.IsType(face) or (Attachment.IsType(face) and face.HasTrait("PSIONIC")):
                    face.Reveal(player, effect)
                    break

        encounter_deck.ShuffleWithDiscardPile(False, effect)

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

    return AbilityFactoryCampaign.WhenCampaignSetupExpertOnly(
        action,
        campaign_id=CAMPAIGN_ID,
    )


def CampaignSetup(level: int) -> List['Ability']:
    abilities: List['Ability'] = []

    if level >= 2:
        abilities.append(PutEarnedCampaignEnvironmentsIntoPlay())

    if level == 2:
        abilities.extend([
            EachPlayerSearchForCardForSavedMorlock(),
            GiveEachEnemyToughForCampaignEnvironment(),
        ])
    elif level == 3:
        abilities.extend([
            PlaceMomentumCountersOnJuggernaut(),
            DealBlackTomAndCreepingWillows(),
        ])
    elif level == 4:
        abilities.extend([
            RevealTeleportedAwayWithCampaignThreat(),
            ApplyPreviousHopeDamage(3, "Scenario 4 Hope Damage Placement"),
        ])
    elif level == 5:
        abilities.extend([
            AddThreatToStryfesGrasp(),
            ApplyPreviousHopeDamage(4, "Scenario 5 Hope Damage Placement"),
            EachPlayerRevealMinionOrPsionicAttachment(),
        ])

    abilities.append(SetupCampaignPlayerSideScheme(level))

    if level >= 2:
        abilities.append(
            AbilityFactoryCampaign.ExpertCampaignSetPlayersHPToTheirRemainingHP(
                campaign_id=CAMPAIGN_ID,
            )
        )
        if level in [2, 4]:
            abilities.append(ExpertCampaignEachPlayerMayHealAtAccelerationCost())
        else:
            abilities.append(
                AbilityFactoryCampaign.ExpertCampaignEachPlayerMayDealFacedownEncounterCardYpHealHP(
                    1,
                    campaign_id=CAMPAIGN_ID,
                )
            )

    return abilities
