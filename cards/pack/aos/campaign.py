from . import *


CAMPAIGN_ID = "agents_of_shield"

BOARD_MEMBERS = {
    "Chief Medical Officer": "50181a,50181b",
    "Chief Surveillance Officer": "50182a,50182b",
    "Chief Tactical Officer": "50183a,50183b",
}

INTERFERENCE_IDS = ["50184a", "50184b", "50184c"]
EVIDENCE_GROUPS = [
    ["50185", "50186", "50187"],
    ["50188", "50189", "50190"],
    ["50191", "50192", "50193"],
]
EVIDENCE_IDS = [card_id for group in EVIDENCE_GROUPS for card_id in group]

ADAPTOID_ENVIRONMENT_IDS = ["50109", "50110", "50111", "50112"]
SURVIVING_THUNDERBOLT_SETS = {
    "50139": "gravitational_pull",
    "50143": "hard_sound",
    "50148": "pale_little_spider",
    "50152": "power_of_the_atom",
    "50156": "supersonic",
    "50161": "the_leaper",
}


def _campaign_list(key: str, effect: 'Effect') -> List[str]:
    from game.operate.campaign_logs import CampaignLog

    return CampaignLog.GetListInternal(key, effect)


def _campaign_int(key: str, effect: 'Effect') -> int:
    from game.operate.campaign_logs import CampaignLog

    return CampaignLog.GetIntInternal(key, effect)


def _campaign_flag(key: str, effect: 'Effect') -> bool:
    from game.operate.campaign_logs import CampaignLog

    return CampaignLog.GetStrInternal(key, effect).strip().lower() in {
        "1", "on", "true", "yes",
    }


def _campaign_card_or_generate(card_ids: str, effect: 'Effect') -> 'CardFace':
    ids = card_ids.split(",")
    areas = [
        Worlds.GetEncounterDeck(effect),
        Worlds.AsideDeck(effect),
        effect.world.area_evidence,
        effect.world.area_removed,
    ]
    for area in areas:
        face = area.FindCard(card_ids=ids)
        if face:
            return face

    for face in Worlds.GetOnFieldCards(effect):
        linked_ids = [face.paper.card_id] + [
            back.paper.card_id for back in face.card.back_faces
        ]
        if any(card_id in ids for card_id in linked_ids):
            return face

    return CardFactory.GenerateCard(
        card_ids,
        Worlds.AsideDeck(effect),
        effect.world,
    ).face


def PrepareEvidenceEnvelopes() -> 'Ability':
    def action(effect: 'Effect', message: 'Message.WhenCampaignSetup') -> None:
        import random as python_random

        evidence = {
            card_id: _campaign_card_or_generate(card_id, effect)
            for card_id in EVIDENCE_IDS
        }

        seed = _campaign_int("Evidence Seed", effect)
        randomizer = python_random.Random(seed)
        aim_ids: List[str] = []
        for group in EVIDENCE_GROUPS:
            choices = group[:]
            randomizer.shuffle(choices)
            aim_ids.append(choices[0])

        earned_ids = [
            card_id for card_id in _campaign_list("Evidence Earned", effect)
            if card_id in EVIDENCE_IDS and card_id not in aim_ids
        ]

        villain = Worlds.FindVillain(effect)
        assert villain

        aim_envelope = Worlds.ScenarioDeck(effect, "A.I.M.Envelope")
        aim_envelope.Create(effect, villain)
        aim_envelope.PushCards([evidence[card_id] for card_id in aim_ids], effect)

        shield_ids = [
            card_id for card_id in EVIDENCE_IDS
            if card_id not in aim_ids and card_id not in earned_ids
        ]
        shield_envelope = Worlds.ScenarioDeck(effect, "S.H.I.E.L.D.Envelope")
        shield_envelope.Create(effect, villain)
        shield_envelope.PushCards([evidence[card_id] for card_id in shield_ids], effect)

        # Earned Evidence is campaign information, not a card in play or in
        # either envelope. Its Setup instruction resolves separately below.
        Faces.RemoveAllFromGame(
            [evidence[card_id] for card_id in earned_ids],
            effect,
        )

    return AbilityFactoryCampaign.WhenCampaignSetup(
        action,
        campaign_id=CAMPAIGN_ID,
    )


def PrepareExecutiveBoard(level: int) -> 'Ability':
    def action(effect: 'Effect', message: 'Message.WhenCampaignSetup') -> None:
        first_player = Worlds.GetFirstPlayer(effect)

        for name, linked_ids in BOARD_MEMBERS.items():
            member = _campaign_card_or_generate(linked_ids, effect)
            if level == 1:
                secrets = 2
            else:
                secrets = _campaign_int(
                    f"Scenario {level - 1} {name} Secret Counters",
                    effect,
                )

            if _campaign_flag(f"{name} Flipped", effect):
                # A level-five scenario can have put the printed Setup face in
                # play before campaign setup. Move it back to the supported
                # staging area so restored counters cannot trigger its normal
                # in-game flip response.
                if member.IsInPlay():
                    Faces.MoveAllTo([member], Worlds.AsideDeck(effect), effect)
                if secrets:
                    Faces.PlaceCountersOn([member], secrets, "secret", effect)
                if Environment.IsType(member):
                    member.card.Flip(effect, call_reveal=False, ui_group=True)
                member.card.face.PutIntoPlay(first_player, effect)
            else:
                if not member.IsInPlay():
                    member.PutIntoPlay(first_player, effect)
                if secrets:
                    Faces.PlaceCountersOn([member], secrets, "secret", effect)

            if Attachment.IsType(member.card.face):
                CampaignLog.SetStr(f"{name} Flipped", "Yes", effect.world)

        generated_interference: List['CardFace'] = []
        encounter_deck = Worlds.GetEncounterDeck(effect)
        for card_id in INTERFERENCE_IDS:
            if not encounter_deck.FindCard(card_ids=[card_id]):
                generated_interference.append(
                    CardFactory.GenerateCard(
                        card_id,
                        Worlds.AsideDeck(effect),
                        effect.world,
                    ).face
                )
        if generated_interference:
            Faces.ShuffleAllTo(generated_interference, encounter_deck, effect)

    return AbilityFactoryCampaign.WhenCampaignSetup(
        action,
        campaign_id=CAMPAIGN_ID,
    )


def ResolveEarnedEvidenceSetup() -> 'Ability':
    def action(effect: 'Effect', message: 'Message.WhenCampaignSetup') -> None:
        earned_ids = set(_campaign_list("Evidence Earned", effect))
        for card_id in EVIDENCE_IDS:
            if card_id not in earned_ids:
                continue
            evidence = effect.world.area_removed.FindCard(card_ids=[card_id])
            if evidence and Evidence.IsType(evidence):
                evidence.Setup(False)

    return AbilityFactoryCampaign.WhenCampaignSetup(
        action,
        campaign_id=CAMPAIGN_ID,
    )


def ResolveCampaignVictory(level: int) -> 'Ability':
    def action(effect: 'Effect', message: 'Message.WhenGameOver') -> None:
        members = Worlds.FindCardsOnField(effect, trait="BOARD MEMBER")

        if level <= 4:
            for name in BOARD_MEMBERS:
                member = next((face for face in members if face.name == name), None)
                if not member:
                    member = next((
                        face for face in members
                        if any(back.name == name for back in face.card.back_faces)
                    ), None)
                if not member:
                    continue
                CampaignLog.SetStr(
                    f"Scenario {level} {name} Secret Counters",
                    str(member.GetCounters("secret")),
                    effect.world,
                )
                if Attachment.IsType(member):
                    CampaignLog.SetStr(
                        f"{name} Flipped",
                        "Yes",
                        effect.world,
                    )

        investigated = any(
            Environment.IsType(member) and member.GetCounters("secret") == 0
            for member in members
        )
        if not investigated:
            return

        shield_envelope = Worlds.ScenarioDeck(effect, "S.H.I.E.L.D.Envelope")
        if not shield_envelope.initialize:
            return
        earned_ids = [
            card_id for card_id in _campaign_list("Evidence Earned", effect)
            if card_id in EVIDENCE_IDS
        ]
        candidates = [
            evidence
            for evidence in shield_envelope.deck.FindCards(card_type=Evidence)
            if evidence.paper.card_id not in earned_ids
        ]
        if not candidates:
            return

        evidence = Rand.RandomChoice(candidates, effect)
        first_player = Worlds.GetFirstPlayer(effect)
        Faces.LookAt([evidence], first_player, effect)
        Faces.RemoveAllFromGame([evidence], effect)

        earned_ids.append(evidence.paper.card_id)
        CampaignLog.SetStr(
            "Evidence Earned",
            ";".join(earned_ids),
            effect.world,
        )

    return Ability(
        AbilityType.ForcedResponse,
        Message.WhenGameOver,
        [
            lambda effect, message: message.players_won,
            lambda effect, message:
                Worlds.IsCampaignSelected(effect, CAMPAIGN_ID),
        ],
        action,
    ).NoOutOfPlayLimit()


def ApplyBatrocCampaignSetup() -> 'Ability':
    def action(effect: 'Effect', message: 'Message.WhenCampaignSetup') -> None:
        alert_level = Worlds.FindCardOnField(
            effect,
            name="Alert Level",
            card_type=Environment,
        )
        threat = _campaign_int(
            "Scenario 1 Minions and side schemes in play",
            effect,
        )
        if alert_level and threat:
            Faces.PlaceTokensOn([alert_level], threat, "threat", effect)

    return AbilityFactoryCampaign.WhenCampaignSetup(
        action,
        campaign_id=CAMPAIGN_ID,
    )


def ApplyMODOKCampaignSetup() -> 'Ability':
    def action(effect: 'Effect', message: 'Message.WhenCampaignSetup') -> None:
        holding_cell = Worlds.FindCardOnField(
            effect,
            name="Holding Cell",
            card_type=Environment,
        )
        if not holding_cell:
            return

        additional_locks = 3 * len(Worlds.GetPlayers(effect))
        Faces.PlaceCountersOn([holding_cell], additional_locks, "lock", effect)

        rescued_captives = _campaign_int(
            "Scenario 2 Rescued Captives",
            effect,
        )
        if rescued_captives:
            Faces.RemoveCountersOn(
                [holding_cell],
                rescued_captives,
                "lock",
                effect,
            )

    return AbilityFactoryCampaign.WhenCampaignSetup(
        action,
        campaign_id=CAMPAIGN_ID,
    )


def ApplyBaronZemoCampaignSetup() -> 'Ability':
    def action(effect: 'Effect', message: 'Message.WhenCampaignSetup') -> None:
        first_player = Worlds.GetFirstPlayer(effect)
        for card_id in _campaign_list(
            "Scenario 3 Adaptoid environments",
            effect,
        ):
            if card_id in ADAPTOID_ENVIRONMENT_IDS:
                card = CardFactory.GenerateCard(
                    card_id,
                    Worlds.AsideDeck(effect),
                    effect.world,
                )
                card.face.PutIntoPlay(first_player, effect)

        encounter_deck = Worlds.GetEncounterDeck(effect)
        CardFactory.GenerateCards(
            ["50113", "50113", "50113", "50113"],
            encounter_deck,
            effect.world,
        )

        added_sets: Set[str] = set()
        for card_id in _campaign_list(
            "Scenario 4 Surviving Thunderbolts",
            effect,
        ):
            encounter_set = SURVIVING_THUNDERBOLT_SETS.get(card_id)
            if encounter_set and encounter_set not in added_sets:
                CardFactory.GenerateCards(
                    CardFactory.LoadEncounterSet(encounter_set),
                    encounter_deck,
                    effect.world,
                )
                added_sets.add(encounter_set)

        encounter_deck.Shuffle(effect)

    return AbilityFactoryCampaign.WhenCampaignSetup(
        action,
        campaign_id=CAMPAIGN_ID,
    )


def ExpertCampaignEachPlayerMayHealAtSecretCost() -> 'Ability':
    def action(effect: 'Effect', message: 'Message.WhenCampaignSetup') -> None:
        for player in Worlds.GetPlayers(effect):
            identity = player.GetIdentity()
            recovery = identity.GetAlterEgoFace().recover

            def heal(targets: Sequence['CardFace'], player=player, recovery=recovery) -> None:
                Faces.PlaceCountersOn(targets, 1, "secret", effect)
                effect.this.HealthUnits([player.GetIdentity()], recovery, effect)

            player.MayChooseOneAbility(
                effect,
                AbilityFactory.ForChoiceAbility(
                    f"Place 1 secret counter on a Board Member environment to heal {recovery} damage from their identity",
                    heal,
                ).SetTarget(Environment, trait="BOARD MEMBER"),
            )

    return AbilityFactoryCampaign.WhenCampaignSetupExpertOnly(
        action,
        campaign_id=CAMPAIGN_ID,
    )


def CampaignSetup(level: int) -> List['Ability']:
    abilities: List['Ability'] = [
        PrepareEvidenceEnvelopes(),
        PrepareExecutiveBoard(level),
        ResolveEarnedEvidenceSetup(),
        ResolveCampaignVictory(level),
    ]

    if level == 2:
        abilities.append(ApplyBatrocCampaignSetup())
    elif level == 3:
        abilities.append(ApplyMODOKCampaignSetup())
    elif level == 5:
        abilities.append(ApplyBaronZemoCampaignSetup())

    if level >= 2:
        abilities.extend([
            AbilityFactoryCampaign.CampaignSetPlayersHPToTheirRemainingHP(
                campaign_id=CAMPAIGN_ID,
            ),
            ExpertCampaignEachPlayerMayHealAtSecretCost(),
        ])

    return abilities
