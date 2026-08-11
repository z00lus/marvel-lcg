import importlib
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from engine import Engine


hercules_pack = importlib.import_module("cards.pack.hercules")
defeat_hydra = importlib.import_module("cards.pack.hercules.hercules.59002")
embody_pathos = importlib.import_module("cards.pack.hercules.hercules.59003")
protect_humanity = importlib.import_module("cards.pack.hercules.hercules.59004")
gauntlets = importlib.import_module("cards.pack.hercules.hercules.59013")
marvel_boy = importlib.import_module("cards.pack.hercules.59025")


class HerculesScriptLoadTests(TestCase):

    def test_every_hercules_script_builds_its_abilities(self):
        modules = [
            "cards.pack.hercules.hercules.59001a",
            "cards.pack.hercules.hercules.59001b",
            *(
                f"cards.pack.hercules.hercules.{card_id}"
                for card_id in range(59002, 59018)
            ),
            *(
                f"cards.pack.hercules.{card_id}"
                for card_id in [
                    59018, 59019, 59020, 59022, 59023,
                    59024, 59025, 59026, 59028,
                ]
            ),
        ]

        for module_name in modules:
            with self.subTest(module=module_name):
                abilities = importlib.import_module(module_name).GetAbilities()
                self.assertTrue(abilities)


class LaborLifecycleTests(TestCase):

    def test_labor_that_leaves_play_returns_to_bottom_of_labor_deck(self):
        ability = hercules_pack.ReturnLaborToDeckWhenItLeavesPlay()
        labor_deck = Mock()
        player = Mock()
        player.special_decks = {hercules_pack.LABOR_DECK: labor_deck}
        labor = Mock()
        labor.GetOwnerPlayer.return_value = player
        effect = Mock()
        effect.this = labor
        message = Mock()
        message.into_area.flags.is_victory_display = False

        with patch.object(hercules_pack.Faces, "MoveAllToDeck") as move_to_deck:
            ability.operation(effect, message)

        move_to_deck.assert_called_once_with(
            [labor], labor_deck, "Bottom", effect,
        )

    def test_labor_in_victory_display_stays_there(self):
        ability = hercules_pack.ReturnLaborToDeckWhenItLeavesPlay()
        effect = Mock()
        message = Mock()
        message.into_area.flags.is_victory_display = True

        with patch.object(hercules_pack.Faces, "MoveAllToDeck") as move_to_deck:
            ability.operation(effect, message)

        move_to_deck.assert_not_called()

    def test_defeat_hydra_is_discarded_when_no_minion_is_found(self):
        ability = defeat_hydra.GetAbilities()[1]
        labor = Mock()
        effect = Mock()
        effect.this.CastTo.return_value = labor
        message = Mock()

        with (
            patch.object(defeat_hydra.Find, "FindAndReveal", return_value=None),
            patch.object(defeat_hydra.Faces, "DiscardAll") as discard,
        ):
            ability.operation(effect, message)

        discard.assert_called_once_with([labor], effect)

    def test_protect_humanity_is_discarded_when_amadeus_is_not_found(self):
        ability = protect_humanity.GetAbilities()[1]
        labor = Mock()
        effect = Mock()
        effect.this = labor
        message = Mock()

        with (
            patch.object(protect_humanity.Find, "FindAndPutIntoPlay", return_value=None),
            patch.object(protect_humanity.Faces, "DiscardAll") as discard,
        ):
            ability.operation(effect, message)

        discard.assert_called_once_with([labor], effect)


class EmbodyPathosTests(TestCase):

    def test_reveal_treats_every_per_hero_icon_as_one(self):
        ability = embody_pathos.GetAbilities()[1]
        labor = Mock()
        effect = Mock()
        effect.this.CastTo.return_value = labor
        effect.world = SimpleNamespace(started_player_num=3)
        player = Mock()
        message = Mock()
        message.GetToPlayer.return_value = player

        scheme = Mock()
        scheme.paper.desc = {
            "StartingThreat": "2*",
            "Hinder": "2*",
        }
        scheme.start_threat = 6
        scheme.printed_hinder = 6
        scheme.hinder = 6
        scheme.IsInPlay.return_value = True

        def reveal(to_player, by_effect):
            self.assertIs(to_player, player)
            self.assertIs(by_effect, effect)
            self.assertEqual(effect.world.started_player_num, 1)
            self.assertEqual(scheme.start_threat, 2)
            self.assertEqual(scheme.printed_hinder, 2)
            scheme.hinder = 2
            return Mock()

        scheme.Reveal.side_effect = reveal

        with (
            patch.object(embody_pathos.Find, "Find", return_value=scheme),
            patch.object(embody_pathos.Faces, "DiscardAll") as discard,
        ):
            ability.operation(effect, message)

        self.assertEqual(effect.world.started_player_num, 3)
        self.assertEqual(scheme.start_threat, 6)
        self.assertEqual(scheme.printed_hinder, 6)
        scheme.SetTokens.assert_not_called()
        scheme.GainHinder.assert_called_once_with(4, effect)
        labor.AttachTo2.assert_called_once_with(scheme, effect)
        labor.PlaceThreatOnSchemes.assert_called_once_with([scheme], 6, effect)
        discard.assert_not_called()

    def test_player_count_is_restored_when_revealing_the_scheme_fails(self):
        ability = embody_pathos.GetAbilities()[1]
        effect = Mock()
        effect.this.CastTo.return_value = Mock()
        effect.world = SimpleNamespace(started_player_num=4)
        message = Mock()

        scheme = Mock()
        scheme.paper.desc = {
            "StartingThreat": "2*",
            "Hinder": "1*",
        }
        scheme.start_threat = 8
        scheme.printed_hinder = 4
        scheme.IsInPlay.return_value = False
        scheme.Reveal.side_effect = RuntimeError("reveal failed")

        with patch.object(embody_pathos.Find, "Find", return_value=scheme):
            with self.assertRaisesRegex(RuntimeError, "reveal failed"):
                ability.operation(effect, message)

        self.assertEqual(effect.world.started_player_num, 4)
        self.assertEqual(scheme.start_threat, 8)
        self.assertEqual(scheme.printed_hinder, 4)

    def test_is_discarded_when_no_side_scheme_is_found(self):
        ability = embody_pathos.GetAbilities()[1]
        labor = Mock()
        effect = Mock()
        effect.this.CastTo.return_value = labor
        message = Mock()

        with (
            patch.object(embody_pathos.Find, "Find", return_value=None),
            patch.object(embody_pathos.Faces, "DiscardAll") as discard,
        ):
            ability.operation(effect, message)

        discard.assert_called_once_with([labor], effect)


class GauntletsOfHerculesTests(TestCase):

    def test_cannot_exhaust_gauntlets_when_no_gift_is_controlled(self):
        ability = gauntlets.GetAbilities()[0]
        condition = ability.conditions[-1]
        player = Mock()
        player.GetControlCards.return_value = []
        effect = Mock()
        effect.GetInitiator.return_value = player

        self.assertFalse(condition(effect, Mock()))

    def test_can_exhaust_gauntlets_when_a_gift_is_controlled(self):
        ability = gauntlets.GetAbilities()[0]
        condition = ability.conditions[-1]
        player = Mock()
        player.GetControlCards.return_value = [Mock()]
        effect = Mock()
        effect.GetInitiator.return_value = player

        self.assertTrue(condition(effect, Mock()))


class MarvelBoyAdditionalCostTests(TestCase):

    def GetCostAndEffect(self):
        cost = marvel_boy.GetAbilities()[0].cost_funcs[0]
        identity = Mock()
        player = Mock()
        player.GetIdentity.return_value = identity
        effect = Mock()
        effect.GetInitiator.return_value = player
        source = Mock()
        cost.cost_legal_targets = [source]
        return cost, effect, identity, source

    def test_stalwart_identity_rejects_confused_cost_before_commit(self):
        cost, effect, identity, source = self.GetCostAndEffect()
        identity.HasTrait.return_value = False
        identity.CanbeConfused.return_value = False

        with patch.object(cost.selector, "GetAllLegalTargets", return_value=[source]):
            self.assertFalse(cost.ValidatePreparedCost(effect))

        identity.GainStatus.assert_not_called()

    def test_stalwart_identity_hides_the_unpayable_play_option(self):
        cost, effect, identity, source = self.GetCostAndEffect()
        identity.HasTrait.return_value = False
        identity.CanbeConfused.return_value = False

        with patch.object(cost.selector, "GetAllLegalTargets", return_value=[source]):
            self.assertFalse(cost.HasTargets(effect))

    def test_eternal_identity_does_not_need_to_accept_confused(self):
        cost, effect, identity, source = self.GetCostAndEffect()
        identity.HasTrait.return_value = True
        identity.CanbeConfused.return_value = False

        with patch.object(cost.selector, "GetAllLegalTargets", return_value=[source]):
            self.assertTrue(cost.ValidatePreparedCost(effect))


class ProtectHumanityTests(TestCase):

    def test_ally_condition_uses_player_who_has_the_obligation(self):
        ability = protect_humanity.GetAbilities()[2]
        condition = ability.conditions[-1]

        player = Mock()
        player.GetControlAllies.return_value = [Mock()]
        obligation = Mock()
        obligation.GetGaveToPlayer.return_value = player
        effect = Mock()
        effect.this.CastTo.return_value = obligation
        effect.GetInitiator.side_effect = AssertionError("attacker is not a player")

        self.assertTrue(condition(effect, Mock()))
        effect.GetInitiator.assert_not_called()

    def test_ally_condition_is_false_without_a_controlled_ally(self):
        ability = protect_humanity.GetAbilities()[2]
        condition = ability.conditions[-1]

        player = Mock()
        player.GetControlAllies.return_value = []
        obligation = Mock()
        obligation.GetGaveToPlayer.return_value = player
        effect = Mock()
        effect.this.CastTo.return_value = obligation

        self.assertFalse(condition(effect, Mock()))
