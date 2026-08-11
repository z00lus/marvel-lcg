from . import *


CAMPAIGN_ID = "age_of_apocalypse"

MISSION_SIDE_SCHEMES = ["45166a", "45167a", "45168a", "45169a"]
PROTECT_THE_PROFESSOR = "45170a"
OVERSEERS = ["45179a", "45180a", "45181a", "45182a", "45183a"]
CAMPAIGN_ALLIES = ["45172", "45173", "45174", "45175"]


def _log_list(key: str, effect: 'Effect') -> List[str]:
    from game.operate.campaign_logs import CampaignLog

    return CampaignLog.GetListInternal(key, effect)


def _log_choice(key: str, allowed: Sequence[str], effect: 'Effect') -> str:
    from game.operate.campaign_logs import CampaignLog

    selected = CampaignLog.GetStrInternal(key, effect)
    return selected if selected in allowed else ""


def _selected_or_random(
    key: str,
    all_ids: Sequence[str],
    unavailable: Sequence[str],
    effect: 'Effect',
) -> str:
    selected = _log_choice(key, all_ids, effect)
    if selected and selected not in unavailable:
        return selected

    available = [card_id for card_id in all_ids if card_id not in unavailable]
    return Rand.RandomChoice(available, effect) if available else ""


def _generate_into_player_deck(card_id: str, player: 'Player', effect: 'Effect') -> None:
    if not card_id:
        return
    CardFactory.GenerateCard(card_id, player.player_deck, effect.world)
    player.player_deck.Shuffle(effect)


def AddPreviousMissionRewardsAndPenalties(level: int) -> 'Ability':
    def action(effect: 'Effect', message: 'Message.WhenCampaignSetup') -> None:
        if level <= 1:
            return

        removed = set(_log_list("Mission Side Schemes Removed from campaign", effect))
        defeated = set(_log_list("Mission Side Schemes Defeated", effect))
        removed |= defeated

        for player in Worlds.GetPlayers(effect):
            player_id = player.player_id

            if "45166a" in defeated:
                _generate_into_player_deck("45176", player, effect)

            if "45167a" in removed:
                if "45167a" in defeated:
                    from game.operate.campaign_logs import CampaignLog
                    upgrade_id = CampaignLog.GetStrInternal(
                        f"Player {player_id + 1} Campaign Aspect Upgrade",
                        effect,
                    )
                    _generate_into_player_deck(upgrade_id, player, effect)
                else:
                    _generate_into_player_deck("45178", player, effect)

            if "45168a" in removed and "45168a" in defeated:
                from game.operate.campaign_logs import CampaignLog
                support_id = CampaignLog.GetStrInternal(
                    f"Player {player_id + 1} Campaign Aspect Support",
                    effect,
                )
                _generate_into_player_deck(support_id, player, effect)

            if "45169a" in defeated:
                ally_id = _log_choice(
                    f"Player {player_id + 1} Campaign Ally",
                    CAMPAIGN_ALLIES,
                    effect,
                )
                _generate_into_player_deck(ally_id, player, effect)

        if "45168a" in removed and "45168a" not in defeated:
            sea_wall = CardFactory.GenerateCard(
                "45177",
                Worlds.AsideDeck(effect),
                effect.world,
            ).face
            Faces.ShuffleAllTo([sea_wall], "EncounterDeck", effect)

    return AbilityFactoryCampaign.WhenCampaignSetup(action, campaign_id=CAMPAIGN_ID)


def ShuffleAgeOfApocalypseSetIntoEncounterDeck() -> 'Ability':
    def action(effect: 'Effect', message: 'Message.WhenCampaignSetup') -> None:
        faces = [
            CardFactory.GenerateCard(
                card_id,
                Worlds.AsideDeck(effect),
                effect.world,
            ).face
            for card_id in ["45164", "45164", "45165", "45165"]
        ]
        Faces.ShuffleAllTo(faces, "EncounterDeck", effect)

    return AbilityFactoryCampaign.WhenCampaignSetup(action, campaign_id=CAMPAIGN_ID)


def SetupMission(level: int) -> 'Ability':
    def action(effect: 'Effect', message: 'Message.WhenCampaignSetup') -> None:
        from game.operate.campaign_logs import CampaignLog

        first_player = Worlds.GetFirstPlayer(effect)
        CampaignLog.SetStr("Age of Apocalypse Scenario", str(level), effect.world)

        removed_missions = set(_log_list("Mission Side Schemes Removed from campaign", effect))
        removed_missions |= set(_log_list("Mission Side Schemes Defeated", effect))
        if level == 5:
            mission_id = PROTECT_THE_PROFESSOR
        else:
            mission_id = _selected_or_random(
                f"Scenario {level} Mission Side Scheme",
                MISSION_SIDE_SCHEMES,
                list(removed_missions),
                effect,
            )

        defeated_overseers = _log_list("Overseers Defeated", effect)
        overseer_id = _selected_or_random(
            f"Scenario {level} Overseer",
            OVERSEERS,
            defeated_overseers,
            effect,
        )

        if mission_id:
            mission = CardFactory.GenerateCard(
                f"{mission_id},{mission_id[:-1]}b",
                Worlds.AsideDeck(effect),
                effect.world,
            ).face
            mission.PutIntoPlay(first_player, effect)

        if overseer_id:
            overseer = CardFactory.GenerateCard(
                f"{overseer_id},{overseer_id[:-1]}b",
                Worlds.AsideDeck(effect),
                effect.world,
            ).face
            overseer.card.bind_discard_pile = Worlds.GetEncounterDiscardPile(effect)
            Faces.MoveAllTo([overseer], Worlds.ScenarioArea(effect, "MissionArea"), effect)

        mission_team = CardFactory.GenerateCard(
            "45171a,45171b",
            Worlds.AsideDeck(effect),
            effect.world,
        ).face
        mission_team.PutIntoPlay(first_player, effect, under_control=True)

        # Resolve the selected mission's campaign-log Setup instruction.
        if mission_id == "45166a":
            for _ in Worlds.GetPlayers(effect):
                CardFactory.GenerateCard("45176", effect.world.aside_deck, effect.world)
        elif mission_id == "45167a":
            for player in Worlds.GetPlayers(effect):
                _generate_into_player_deck("45178", player, effect)
        elif mission_id == "45168a":
            sea_wall = CardFactory.GenerateCard(
                "45177",
                Worlds.AsideDeck(effect),
                effect.world,
            ).face
            Faces.ShuffleAllTo([sea_wall], "EncounterDeck", effect)
        elif mission_id == "45169a":
            for card_id in CAMPAIGN_ALLIES:
                CardFactory.GenerateCard(card_id, effect.world.aside_deck, effect.world)

    return AbilityFactoryCampaign.WhenCampaignSetup(action, campaign_id=CAMPAIGN_ID)


def EachPlayerSearchForAnAlly(level: int) -> 'Ability':
    def action(effect: 'Effect', message: 'Message.WhenCampaignSetup') -> None:
        for player in Worlds.GetPlayers(effect):
            finder = None
            if level == 5 and Worlds.IsExpert(effect):
                hero_traits = set(player.GetIdentity().GetHeroFace().traits)
                finder = CardFinder(
                    check_effect_fn=lambda check_effect, face, hero_traits=hero_traits:
                        bool(hero_traits.intersection(face.traits))
                )

            ally = Search.PlayerCard(
                effect,
                player,
                include_player_deck=True,
                card_type=Ally,
                finder=finder,
                not_move=True,
            )
            if ally:
                player.GainCard(ally, effect)
                if player.player_deck.GetSize():
                    player.player_deck.Shuffle(effect)

    return AbilityFactoryCampaign.WhenCampaignSetup(action, campaign_id=CAMPAIGN_ID)


def ExpertCampaignEachPlayerMayHealAtMissionThreatCost() -> 'Ability':
    def action(effect: 'Effect', message: 'Message.WhenCampaignSetup') -> None:
        from game.operate.campaign_logs import CampaignLog

        mission = Worlds.FindCardOnField(
            effect,
            card_type=EncounterSideScheme,
            trait="MISSION",
        )
        if not mission:
            return

        for player in Worlds.GetPlayers(effect):
            if (
                not Worlds.IsExpert(effect)
                and not CampaignLog.GetIntByPlayer(
                    "Remaining hit points",
                    player.player_id,
                    effect,
                )
            ):
                continue

            def heal_identity(targets: Sequence['CardFace'], player=player) -> None:
                effect.this.PlaceThreatOnSchemes([mission], 3, effect)
                effect.this.HealthUnits(targets, "All", effect)

            player.MayChooseOneAbility(
                effect,
                AbilityFactory.ForChoiceAbility(
                    "Place 3 threat on the MISSION side scheme to heal their identity to its full hit point value",
                    heal_identity,
                ).SetTarget([player.GetIdentity()], canbe_heal=True),
            )

    return AbilityFactoryCampaign.WhenCampaignSetup(
        action,
        campaign_id=CAMPAIGN_ID,
    )


def CampaignSetup(level: int) -> List['Ability']:
    abilities: List['Ability'] = [
        AddPreviousMissionRewardsAndPenalties(level),
        ShuffleAgeOfApocalypseSetIntoEncounterDeck(),
        SetupMission(level),
    ]

    if level >= 2:
        abilities.extend([
            AbilityFactoryCampaign.CampaignSetPlayersHPToTheirRemainingHP(
                campaign_id=CAMPAIGN_ID,
            ),
            ExpertCampaignEachPlayerMayHealAtMissionThreatCost(),
        ])

    abilities.append(EachPlayerSearchForAnAlly(level))
    return abilities
