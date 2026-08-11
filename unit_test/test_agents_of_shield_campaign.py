from importlib import import_module
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, call, patch

from engine import Engine  # noqa: F401 - establishes the project's import order
from cards.pack.aos.campaign import (
    EVIDENCE_IDS,
    PrepareEvidenceEnvelopes,
    PrepareExecutiveBoard,
    ResolveCampaignVictory,
    ResolveEarnedEvidenceSetup,
)
from cards.pack.aos.executive_board_evidence import EvidenceMeans
from cards.pack.aos.shield_executive_board import (
    BoardMemberSecretThreshold,
    IfThereAre3BoardMemberAttachmentsInPlayAfterThisEntersPlay,
    RecordBoardMemberFlipped,
)
from game.message import Message
from game.operate.campaign_logs import CampaignLog
from game.world.world import World


def evidence_face(card_id: str) -> MagicMock:
    face = MagicMock(name=card_id)
    face.paper = SimpleNamespace(card_id=card_id)
    return face


class TestAgentsOfShieldEvidence(unittest.TestCase):

    def test_aos_evidence_and_board_setup_wait_for_campaign_state(self):
        world = SimpleNamespace(
            rule=SimpleNamespace(mode_campaign=SimpleNamespace(val=True)),
            scene=SimpleNamespace(
                campaign=SimpleNamespace(campaign_id="agents_of_shield"),
            ),
        )
        evidence = MagicMock()
        board_member = MagicMock()
        board_member.HasTrait.return_value = True
        ordinary_setup_card = MagicMock()
        ordinary_setup_card.HasTrait.return_value = False

        with patch(
            "game.world.world.Evidence.IsType",
            side_effect=lambda face: face is evidence,
        ):
            self.assertTrue(World.ShouldDeferCampaignCardSetup(world, evidence))
            self.assertTrue(
                World.ShouldDeferCampaignCardSetup(world, board_member)
            )
            self.assertFalse(
                World.ShouldDeferCampaignCardSetup(world, ordinary_setup_card)
            )

        world.scene.campaign.campaign_id = "age_of_apocalypse"
        with patch("game.world.world.Evidence.IsType", return_value=True):
            self.assertFalse(World.ShouldDeferCampaignCardSetup(world, evidence))

    def prepare_envelopes(self, seed: int, earned_ids=None):
        earned_ids = earned_ids or []
        faces = {card_id: evidence_face(card_id) for card_id in EVIDENCE_IDS}
        aim_envelope = MagicMock(name="A.I.M. envelope")
        shield_envelope = MagicMock(name="S.H.I.E.L.D. envelope")
        effect = SimpleNamespace(world=MagicMock())

        def scenario_deck(effect_arg, name):
            self.assertIs(effect_arg, effect)
            return aim_envelope if name == "A.I.M.Envelope" else shield_envelope

        with patch(
            "cards.pack.aos.campaign._campaign_card_or_generate",
            side_effect=lambda card_id, effect_arg: faces[card_id],
        ), patch(
            "cards.pack.aos.campaign._campaign_int",
            return_value=seed,
        ), patch(
            "cards.pack.aos.campaign._campaign_list",
            return_value=earned_ids,
        ), patch(
            "cards.pack.aos.campaign.Worlds.FindVillain",
            return_value=MagicMock(),
        ), patch(
            "cards.pack.aos.campaign.Worlds.ScenarioDeck",
            side_effect=scenario_deck,
        ), patch(
            "cards.pack.aos.campaign.Faces.RemoveAllFromGame",
        ) as remove:
            PrepareEvidenceEnvelopes().operation(effect, SimpleNamespace())

        aim = [face.paper.card_id for face in aim_envelope.PushCards.call_args.args[0]]
        shield = [face.paper.card_id for face in shield_envelope.PushCards.call_args.args[0]]
        removed = [face.paper.card_id for face in remove.call_args.args[0]]
        return aim, shield, removed

    def test_same_seed_builds_the_same_envelopes(self):
        first = self.prepare_envelopes(7)
        second = self.prepare_envelopes(7)

        self.assertEqual(first, second)
        self.assertEqual(first[0], ["50187", "50190", "50192"])
        self.assertEqual(len(first[1]), 6)

    def test_earned_evidence_is_removed_and_excluded_from_both_envelopes(self):
        aim, shield, removed = self.prepare_envelopes(7, ["50185"])

        self.assertNotIn("50185", aim)
        self.assertNotIn("50185", shield)
        self.assertEqual(removed, ["50185"])
        self.assertEqual(set(aim + shield + removed), set(EVIDENCE_IDS))

    def test_earned_evidence_setup_resolves_once_from_removed_area(self):
        evidence = MagicMock()
        removed = MagicMock()
        removed.FindCard.side_effect = lambda *, card_ids: (
            evidence if card_ids == ["50185"] else None
        )
        effect = SimpleNamespace(world=SimpleNamespace(area_removed=removed))
        ability = ResolveEarnedEvidenceSetup()

        with patch(
            "cards.pack.aos.campaign._campaign_list",
            return_value=["50185", "invalid", "50185"],
        ), patch(
            "cards.pack.aos.campaign.Evidence.IsType",
            return_value=True,
        ):
            ability.operation(effect, SimpleNamespace())

        evidence.Setup.assert_called_once_with(False)
        self.assertIs(ability.when, Message.WhenCampaignSetup)

    def test_collection_searches_cannot_choose_the_same_card_id_twice(self):
        players = [MagicMock(name="player one"), MagicMock(name="player two")]
        original_effect = SimpleNamespace(
            this=MagicMock(CastTo=MagicMock(return_value=MagicMock())),
        )
        ability = EvidenceMeans("Protection")

        with patch(
            "cards.pack.aos.executive_board_evidence.Players.ForEachPlayer",
            side_effect=lambda effect, action: [action(player) for player in players],
        ):
            ability.operation(original_effect, SimpleNamespace())

        first_choice = players[0].MayChooseOneAbility.call_args_list[0].args[1]
        second_choice = players[1].MayChooseOneAbility.call_args_list[0].args[1]
        first_card = evidence_face("test-card-a")
        second_card = evidence_face("test-card-b")
        selected = []

        def choose_collection(effect, player, *, check_fn, **kwargs):
            if not selected:
                self.assertTrue(check_fn(first_card.paper))
                selected.append(first_card.paper.card_id)
                return first_card
            self.assertFalse(check_fn(first_card.paper))
            self.assertTrue(check_fn(second_card.paper))
            selected.append(second_card.paper.card_id)
            return second_card

        choice_effect = SimpleNamespace(
            targets=[MagicMock()],
            GetPaidResources=lambda: None,
        )
        with patch(
            "cards.pack.aos.executive_board_evidence.Search.Collection",
            side_effect=choose_collection,
        ), patch(
            "cards.pack.aos.executive_board_evidence.Faces.PlaceCountersOn",
        ), patch(
            "cards.pack.aos.executive_board_evidence.Faces.ShuffleAllTo",
        ):
            first_choice.operation(choice_effect, SimpleNamespace())
            second_choice.operation(choice_effect, SimpleNamespace())

        self.assertEqual(selected, ["test-card-a", "test-card-b"])
        self.assertTrue(ability.ignore.out_of_play)


class TestAgentsOfShieldExecutiveBoard(unittest.TestCase):

    def test_board_member_threshold_uses_scenario_or_encounter_set_expert(self):
        effect = SimpleNamespace(
            world=SimpleNamespace(
                scene=SimpleNamespace(
                    campaign=SimpleNamespace(encounter_sets=["standard"]),
                ),
            ),
        )

        with patch("game.operate.worlds.Worlds.IsExpert", return_value=False):
            self.assertEqual(BoardMemberSecretThreshold(effect), 4)

        effect.world.scene.campaign.encounter_sets = ["standard", "expert_ii"]
        with patch("game.operate.worlds.Worlds.IsExpert", return_value=False):
            self.assertEqual(BoardMemberSecretThreshold(effect), 3)

        effect.world.scene.campaign.encounter_sets = ["standard"]
        with patch("game.operate.worlds.Worlds.IsExpert", return_value=True):
            self.assertEqual(BoardMemberSecretThreshold(effect), 3)

    def test_flipped_board_member_is_recorded(self):
        front = SimpleNamespace(name="Chief Medical Officer")
        aid = SimpleNamespace(card=SimpleNamespace(back_faces=[front]))
        effect = SimpleNamespace(world=MagicMock())

        with patch(
            "cards.pack.aos.shield_executive_board.Worlds.IsCampaignSelected",
            return_value=True,
        ), patch(
            "cards.pack.aos.shield_executive_board.Environment.IsType",
            return_value=True,
        ), patch(
            "cards.pack.aos.shield_executive_board.CampaignLog.SetStr",
        ) as set_log:
            RecordBoardMemberFlipped(aid, effect)

        set_log.assert_called_once_with(
            "Chief Medical Officer Flipped",
            "Yes",
            effect.world,
        )

    def test_flipped_board_member_restores_before_entering_play(self):
        names = [
            "Chief Medical Officer",
            "Chief Surveillance Officer",
            "Chief Tactical Officer",
        ]
        fronts = {}
        for name in names:
            face = MagicMock(name=name)
            face.name = name
            face.IsInPlay.return_value = name == "Chief Medical Officer"
            face.card = MagicMock()
            face.card.face = face
            fronts[name] = face

        medical_aid = MagicMock(name="Medical Officer's Aid")
        fronts["Chief Medical Officer"].card.Flip.side_effect = lambda *args, **kwargs: setattr(
            fronts["Chief Medical Officer"].card,
            "face",
            medical_aid,
        )
        ids_to_name = {
            "50181a,50181b": "Chief Medical Officer",
            "50182a,50182b": "Chief Surveillance Officer",
            "50183a,50183b": "Chief Tactical Officer",
        }
        effect = SimpleNamespace(world=MagicMock())
        encounter_deck = MagicMock()
        encounter_deck.FindCard.return_value = MagicMock()

        with patch(
            "cards.pack.aos.campaign._campaign_card_or_generate",
            side_effect=lambda linked_ids, effect_arg: fronts[ids_to_name[linked_ids]],
        ), patch(
            "cards.pack.aos.campaign._campaign_int",
            return_value=2,
        ), patch(
            "cards.pack.aos.campaign._campaign_flag",
            side_effect=lambda key, effect_arg: key.startswith("Chief Medical"),
        ), patch(
            "cards.pack.aos.campaign.Worlds.GetFirstPlayer",
            return_value=MagicMock(),
        ), patch(
            "cards.pack.aos.campaign.Worlds.GetEncounterDeck",
            return_value=encounter_deck,
        ), patch(
            "cards.pack.aos.campaign.Worlds.AsideDeck",
            return_value=MagicMock(),
        ), patch(
            "cards.pack.aos.campaign.Environment.IsType",
            side_effect=lambda face: face is fronts["Chief Medical Officer"],
        ), patch(
            "cards.pack.aos.campaign.Attachment.IsType",
            side_effect=lambda face: face is medical_aid,
        ), patch(
            "cards.pack.aos.campaign.Faces.MoveAllTo",
        ) as move, patch(
            "cards.pack.aos.campaign.Faces.PlaceCountersOn",
        ) as counters, patch(
            "cards.pack.aos.campaign.CampaignLog.SetStr",
        ) as set_log:
            PrepareExecutiveBoard(2).operation(effect, SimpleNamespace())

        move.assert_called_once()
        counters.assert_any_call(
            [fronts["Chief Medical Officer"]],
            2,
            "secret",
            effect,
        )
        fronts["Chief Medical Officer"].card.Flip.assert_called_once_with(
            effect,
            call_reveal=False,
            ui_group=True,
        )
        medical_aid.PutIntoPlay.assert_called_once()
        fronts["Chief Surveillance Officer"].PutIntoPlay.assert_called_once()
        set_log.assert_called_once_with(
            "Chief Medical Officer Flipped",
            "Yes",
            effect.world,
        )

    def test_three_restored_attachments_cause_immediate_loss(self):
        ability = IfThereAre3BoardMemberAttachmentsInPlayAfterThisEntersPlay()
        effect = SimpleNamespace()

        with patch(
            "cards.pack.aos.shield_executive_board.Worlds.FindCardSizeOnField",
            return_value=3,
        ), patch(
            "cards.pack.aos.shield_executive_board.Worlds.SetGameOver",
        ) as game_over:
            ability.operation(effect, SimpleNamespace())

        game_over.assert_called_once_with(False, effect)
        self.assertIs(ability.when, Message.AfterCardPutIntoPlay)

    def test_all_board_aid_scripts_check_loss_after_entering_play(self):
        for card_id in ("50181b", "50182b", "50183b"):
            abilities = import_module(
                f"cards.pack.aos.shield_executive_board.{card_id}"
            ).GetAbilities()
            self.assertTrue(any(
                ability.when is Message.AfterCardPutIntoPlay
                for ability in abilities
            ), card_id)

        tactical_source = import_module(
            "cards.pack.aos.shield_executive_board.50183b"
        ).GetAbilities()
        self.assertTrue(tactical_source)

    def test_medical_aid_offers_both_printed_resolutions(self):
        module = import_module("cards.pack.aos.shield_executive_board.50181b")
        source = MagicMock()
        player = MagicMock()
        effect = SimpleNamespace(
            this=MagicMock(CastTo=MagicMock(return_value=source)),
        )

        with patch.object(module.Worlds, "GetFirstPlayer", return_value=player):
            module.GetAbilities()[1].operation(effect, SimpleNamespace())

        heal, damage = player.ChooseAbilities.call_args.args[1:]
        self.assertEqual(heal.name, "Heal 2 damage from the villain")
        self.assertEqual(
            damage.name,
            "Deal 1 damage to the friendly character with the fewest remaining hit points",
        )
        target = MagicMock()
        choice_effect = SimpleNamespace(
            targets=[target],
            GetPaidResources=lambda: None,
        )
        heal.operation(choice_effect, SimpleNamespace())
        damage.operation(choice_effect, SimpleNamespace())
        source.HealthUnits.assert_called_once_with([target], 2, effect)
        source.DealDamage.assert_called_once_with([target], 1, effect)

    def test_surveillance_aid_places_two_threat_on_main_scheme(self):
        module = import_module("cards.pack.aos.shield_executive_board.50182b")
        source = MagicMock()
        effect = SimpleNamespace(
            this=MagicMock(CastTo=MagicMock(return_value=source)),
        )

        module.GetAbilities()[1].operation(effect, SimpleNamespace())

        source.PlaceThreatOnSchemes.assert_called_once_with(
            "MainScheme",
            2,
            effect,
        )

    def test_tactical_aid_choice_has_text_and_deals_two_damage(self):
        module = import_module("cards.pack.aos.shield_executive_board.50183b")
        source = MagicMock()
        player = MagicMock()
        effect = SimpleNamespace(
            this=MagicMock(CastTo=MagicMock(return_value=source)),
        )

        with patch.object(module.Worlds, "GetFirstPlayer", return_value=player):
            module.GetAbilities()[1].operation(effect, SimpleNamespace())

        choice = player.ChooseAbilities.call_args.args[1]
        self.assertEqual(choice.name, "Deal 2 damage to a friendly character")
        target = MagicMock()
        choice_effect = SimpleNamespace(
            targets=[target],
            GetPaidResources=lambda: None,
        )
        choice.operation(choice_effect, SimpleNamespace())
        source.DealDamage.assert_called_once_with([target], 2, effect)


class TestAgentsOfShieldCampaignResults(unittest.TestCase):

    def make_member(self, name: str, counters: int, back_name: str = ""):
        member = MagicMock(name=name)
        member.name = name
        member.GetCounters.return_value = counters
        member.card = SimpleNamespace(
            back_faces=[SimpleNamespace(name=back_name)] if back_name else [],
        )
        return member

    def test_victory_records_board_state_and_awards_one_evidence(self):
        medical = self.make_member("Chief Medical Officer", 0)
        surveillance = self.make_member("Chief Surveillance Officer", 2)
        tactical = self.make_member(
            "Tactical Officer's Aid",
            1,
            "Chief Tactical Officer",
        )
        members = [medical, surveillance, tactical]
        evidence = evidence_face("50185")
        envelope = SimpleNamespace(initialize=True, deck=MagicMock())
        envelope.deck.FindCards.return_value = [evidence]
        player = MagicMock()
        effect = SimpleNamespace(world=MagicMock())

        with patch(
            "cards.pack.aos.campaign.Worlds.FindCardsOnField",
            return_value=members,
        ), patch(
            "cards.pack.aos.campaign.Environment.IsType",
            side_effect=lambda face: face in (medical, surveillance),
        ), patch(
            "cards.pack.aos.campaign.Attachment.IsType",
            side_effect=lambda face: face is tactical,
        ), patch(
            "cards.pack.aos.campaign.Worlds.ScenarioDeck",
            return_value=envelope,
        ), patch(
            "cards.pack.aos.campaign.Worlds.GetFirstPlayer",
            return_value=player,
        ), patch(
            "cards.pack.aos.campaign.Rand.RandomChoice",
            return_value=evidence,
        ) as random_choice, patch(
            "cards.pack.aos.campaign.Faces.LookAt",
        ) as look_at, patch(
            "cards.pack.aos.campaign.Faces.RemoveAllFromGame",
        ) as remove, patch(
            "cards.pack.aos.campaign._campaign_list",
            return_value=["50186"],
        ), patch(
            "cards.pack.aos.campaign.CampaignLog.SetStr",
        ) as set_log:
            ResolveCampaignVictory(2).operation(
                effect,
                SimpleNamespace(players_won=True),
            )

        set_log.assert_has_calls([
            call(
                "Scenario 2 Chief Medical Officer Secret Counters",
                "0",
                effect.world,
            ),
            call(
                "Scenario 2 Chief Surveillance Officer Secret Counters",
                "2",
                effect.world,
            ),
            call(
                "Scenario 2 Chief Tactical Officer Secret Counters",
                "1",
                effect.world,
            ),
            call("Chief Tactical Officer Flipped", "Yes", effect.world),
            call("Evidence Earned", "50186;50185", effect.world),
        ])
        random_choice.assert_called_once_with([evidence], effect)
        look_at.assert_called_once_with([evidence], player, effect)
        remove.assert_called_once_with([evidence], effect)

    def test_loss_is_rejected_before_campaign_result_operation(self):
        ability = ResolveCampaignVictory(1)

        self.assertFalse(
            ability.conditions[0](None, SimpleNamespace(players_won=False))
        )
        self.assertTrue(ability.ignore.out_of_play)

    def test_no_investigated_member_awards_no_evidence(self):
        member = self.make_member("Chief Medical Officer", 1)
        effect = SimpleNamespace(world=MagicMock())

        with patch(
            "cards.pack.aos.campaign.Worlds.FindCardsOnField",
            return_value=[member],
        ), patch(
            "cards.pack.aos.campaign.Environment.IsType",
            return_value=True,
        ), patch(
            "cards.pack.aos.campaign.Attachment.IsType",
            return_value=False,
        ), patch(
            "cards.pack.aos.campaign.Worlds.ScenarioDeck",
        ) as scenario_deck, patch(
            "cards.pack.aos.campaign.CampaignLog.SetStr",
        ):
            ResolveCampaignVictory(1).operation(
                effect,
                SimpleNamespace(players_won=True),
            )

        scenario_deck.assert_not_called()

    def test_already_earned_evidence_cannot_be_awarded_again(self):
        member = self.make_member("Chief Medical Officer", 0)
        evidence = evidence_face("50185")
        envelope = SimpleNamespace(initialize=True, deck=MagicMock())
        envelope.deck.FindCards.return_value = [evidence]
        effect = SimpleNamespace(world=MagicMock())

        with patch(
            "cards.pack.aos.campaign.Worlds.FindCardsOnField",
            return_value=[member],
        ), patch(
            "cards.pack.aos.campaign.Environment.IsType",
            return_value=True,
        ), patch(
            "cards.pack.aos.campaign.Attachment.IsType",
            return_value=False,
        ), patch(
            "cards.pack.aos.campaign.Worlds.ScenarioDeck",
            return_value=envelope,
        ), patch(
            "cards.pack.aos.campaign._campaign_list",
            return_value=["50185"],
        ), patch(
            "cards.pack.aos.campaign.Rand.RandomChoice",
        ) as random_choice, patch(
            "cards.pack.aos.campaign.Faces.LookAt",
        ) as look_at, patch(
            "cards.pack.aos.campaign.CampaignLog.SetStr",
        ):
            ResolveCampaignVictory(1).operation(
                effect,
                SimpleNamespace(players_won=True),
            )

        random_choice.assert_not_called()
        look_at.assert_not_called()

    def test_export_knows_every_board_state_key(self):
        known = CampaignLog.GetKnownKeys()
        for level in range(1, 5):
            for name in (
                "Chief Medical Officer",
                "Chief Surveillance Officer",
                "Chief Tactical Officer",
            ):
                self.assertIn(
                    f"Scenario {level} {name} Secret Counters",
                    known,
                )
                self.assertIn(f"{name} Flipped", known)


if __name__ == "__main__":
    unittest.main()
