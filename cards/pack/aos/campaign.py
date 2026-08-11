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


def _encounter_card_or_generate(card_id: str, effect: 'Effect') -> 'CardFace':
    face = Worlds.GetEncounterDeck(effect).FindCard(card_ids=[card_id])
    if face:
        return face
    return CardFactory.GenerateCard(
        card_id,
        Worlds.AsideDeck(effect),
        effect.world,
    ).face


def PrepareEvidenceEnvelopes() -> 'Ability':
    def action(effect: 'Effect', message: 'Message.WhenCampaignSetup') -> None:
        import random as python_random

        evidence = {
            card_id: _encounter_card_or_generate(card_id, effect)
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

        first_player = Worlds.GetFirstPlayer(effect)
        for card_id in earned_ids:
            evidence[card_id].PutIntoPlay(first_player, effect)

    return AbilityFactoryCampaign.WhenCampaignSetup(
        action,
        campaign_id=CAMPAIGN_ID,
    )


def PrepareExecutiveBoard(level: int) -> 'Ability':
    def action(effect: 'Effect', message: 'Message.WhenCampaignSetup') -> None:
        first_player = Worlds.GetFirstPlayer(effect)

        for name, linked_ids in BOARD_MEMBERS.items():
            card_id = linked_ids.split(",")[0]
            member = Worlds.GetEncounterDeck(effect).FindCard(card_ids=[card_id])
            if not member:
                member = CardFactory.GenerateCard(
                    linked_ids,
                    Worlds.AsideDeck(effect),
                    effect.world,
                ).face
            member.PutIntoPlay(first_player, effect)

            if level == 1:
                secrets = 2
            else:
                secrets = _campaign_int(
                    f"Scenario {level - 1} {name} Secret Counters",
                    effect,
                )
            if secrets:
                Faces.PlaceCountersOn([member], secrets, "secret", effect)

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


def ResolveEarnedEvidenceSetupAfterMulligans() -> 'Ability':
    def action(effect: 'Effect', message: 'Message.WhenGameWouldBegin') -> None:
        for evidence in effect.world.area_evidence.FindCards(card_type=Evidence):
            evidence.Setup(False)

    return AbilityFactory.WhenGameWouldBegin(
        action,
        conditions=[
            lambda effect, message:
                Worlds.IsCampaignSelected(effect, CAMPAIGN_ID),
        ],
    )


def CampaignSetup(level: int) -> List['Ability']:
    abilities: List['Ability'] = [
        PrepareEvidenceEnvelopes(),
        PrepareExecutiveBoard(level),
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

    abilities.append(ResolveEarnedEvidenceSetupAfterMulligans())
    return abilities
