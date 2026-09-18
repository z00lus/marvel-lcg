"""Focused v1.8 attacks with real cards and deterministic player choices."""

from contextlib import ExitStack
import importlib
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from engine import Engine
from build import Build
from cards.database import CardsDB
from engine.lib.version import Ver
from game.ability import AbilityType
from game.ability.factory import AbilityFactory
from game.card.factory import CardFactory
from game.card.face.base import Enemy
from game.card.face.attribute.can_attack import AttackProperty, CanAttack
from game.effect.rule import GameRule
from game.event.manager import EventManager
from game.message import Message
from game.scene.replay.campaign import CampaignDescriptor
from game.scene.replay.hero import HeroDescriptor
from game.scene.scene import Scene
from game.world.phase import Phase
from game.world.world import World


class OverkillDefenseRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Ver.Initialize()
        if not CardsDB.papers:
            CardsDB.Initialize()
        # CardsDB can hide script import failures; load these explicitly.
        for module in ('cards.pack.cyclops.cyclops.33005', 'cards.pack.vision.26018'):
            assert importlib.import_module(module).GetAbilities()

    def setUp(self):
        stack = ExitStack()
        self.addCleanup(stack.close)
        controller_manager = SimpleNamespace(
            console=SimpleNamespace(TryBreak=lambda world: None),
        )
        stack.enter_context(patch.object(Build, 'release', False))
        stack.enter_context(patch.object(
            Engine, 'game', SimpleNamespace(controller_manager=controller_manager),
            create=True,
        ))
        # Optional choices are supplied explicitly at the relevant windows.
        stack.enter_context(patch.object(EventManager, 'ProcessOptionalEffect', return_value=False))
        manager = SimpleNamespace(skip=SimpleNamespace(is_skipping=True))
        scene = Scene(
            version=str(Ver.version), rules=['v18_all'],
            campaign=CampaignDescriptor(campaign_id='rhino', name='Rhino'),
            players=[HeroDescriptor(
                version='', name='Spider-Man', hero=[], hero_deck=[],
                obligations=[], nemesis_set=[], player_deck=[],
            )],
        )
        self.world = World(scene, [SimpleNamespace(manager=manager)])
        self.world.rule.SetRule(scene.rules, False, 1)
        stack.enter_context(patch.object(
            self.world.render, 'ErrorOccurred',
            side_effect=lambda *args: self.fail(f'Engine error: {args}'),
        ))
        self.player = self.world.players[0]
        self.world.insert = self.MakeCard('rule_a,rule_b', self.world.area_insert)
        self.hero = self.MakeCard('01001a,01001b', self.player.area_hero)
        self.hero.ResetHealth(GameRule(self.hero))
        self.villain = self.MakeCard('01094', self.world.GetScenario().area_villain)
        self.villain.ResetHealth(GameRule(self.villain))
        self.world.phase.SetState(Phase.State.PlayerTurn)
        self.world.current_player = self.player

    def MakeCard(self, card_id, area):
        face = CardFactory.GenerateCard(card_id, area, self.world, ui_render=False).face
        face.ResetKeywords()
        return face

    def AttachExploitWeakness(self, target):
        upgrade = self.MakeCard('33005', self.player.hand_cards)
        self.assertTrue(upgrade.AttachTo2(target, GameRule(upgrade)))

    def ResolveOverkill(self, *, upgrade_on_villain=False, upgrade_on_minion=False):
        if upgrade_on_villain:
            self.AttachExploitWeakness(self.villain)
        minion = self.MakeCard('01110', self.player.engaged_minions)
        minion.ResetHealth(GameRule(minion))
        self.assertEqual(minion.health, 2)
        if upgrade_on_minion:
            self.AttachExploitWeakness(minion)
        villain_health = self.villain.health

        CanAttack.AttackInternal(
            self.hero, [minion], GameRule(self.hero),
            property=AttackProperty(is_basic_power=True, additional_value=3, overkill=True),
        )

        self.assertFalse(minion.IsInPlay())
        return villain_health - self.villain.health

    def test_exploit_weakness_increases_overkill_on_villain(self):
        self.assertEqual(self.ResolveOverkill(upgrade_on_villain=True), 4)

    def test_overkill_without_recipient_modifier(self):
        self.assertEqual(self.ResolveOverkill(), 3)

    def test_modifier_on_primary_contributes_to_excess_only_once(self):
        self.assertEqual(self.ResolveOverkill(upgrade_on_minion=True), 4)

    def test_source_damage_modifier_is_not_applied_again_to_overkill(self):
        instances = []

        def increase_source_damage(effect, message):
            before = message.property.damage
            message.IncreaseDamage(2, effect)
            instances.append((message.IsOverkill(), message.property.damage - before))

        self.hero.effect.RegisterTemp(
            AbilityFactory.WhenUnitWouldTakeDamage(
                AbilityType.Temp0, Enemy, increase_source_damage,
                is_from_attack=True, who_deal_damage=self.hero,
            ),
            unregister_after_exec=False,
        )
        # (5 + 2 source bonus) - 2 HP + 1 recipient bonus = 6.
        self.assertEqual(self.ResolveOverkill(upgrade_on_villain=True), 6)
        self.assertEqual(instances, [(False, 2), (True, 0)])

    def test_exploit_weakness_increases_direct_attack_damage(self):
        self.AttachExploitWeakness(self.villain)
        health = self.villain.health
        CanAttack.AttackInternal(
            self.hero, [self.villain], GameRule(self.hero),
            property=AttackProperty(is_basic_power=True),
        )
        self.assertEqual(health - self.villain.health, 3)

    def test_exploit_weakness_does_not_increase_non_attack_damage(self):
        self.AttachExploitWeakness(self.villain)
        health = self.villain.health
        self.villain.TakeDamageNoDeath(self.hero, 2, GameRule(self.hero))
        self.assertEqual(health - self.villain.health, 2)

    def ResolveDefianceAttack(self, defender_kind):
        ally = self.MakeCard('01050', self.player.allies)
        ally.ResetHealth(GameRule(ally))
        event = self.MakeCard('26018', self.player.hand_cards)
        effect = next(e for e in event.effect.global_effects if e.ability.is_play)
        boost = self.MakeCard('01125', self.villain.components.boostable.GetDeck())
        hero_health, ally_health = self.hero.health, ally.health
        windows = []
        original_being_send = Message.WhenUnitBeingAttack.Send
        original_boost_send = Message.WhenBoostCardWouldTurnedFaceUp.Send

        def choose_defender(message):
            original_being_send(message)
            if defender_kind:
                defender = ally if defender_kind == 'ally' else self.hero
                message.DeclareDefender(defender, GameRule(defender))

        def play_defiance(message):
            original_boost_send(message)
            available = EventManager.FilterAvailableEffects(
                message, [effect], self.player, self.world, None,
            )
            self.assertEqual(available, [effect])
            self.assertTrue(self.player.ResolveEffect(effect, message))
            self.assertTrue(message.is_be_instead)
            windows.append(message)

        with patch.object(Message.WhenUnitBeingAttack, 'Send', choose_defender), \
             patch.object(Message.WhenBoostCardWouldTurnedFaceUp, 'Send', play_defiance):
            CanAttack.AttackInternal(
                self.villain, [self.hero], GameRule(self.villain),
                property=AttackProperty(is_basic_power=True, additional_value=2, do_not_give_boost=True),
            )

        self.assertEqual(len(windows), 1)
        self.assertIs(event.card.area, self.player.discard_pile)
        self.assertIs(boost.card.area, self.world.scenario.encounter_discard_pile)
        expected_defender = ally if defender_kind == 'ally' else self.hero
        self.assertIs(windows[0].would_atk_message.defender, expected_defender)
        self.assertEqual(len(windows[0].being_message.defense_messages), 1)
        return hero_health - self.hero.health, ally_health - ally.health

    def test_defiance_keeps_ally_as_damage_recipient(self):
        self.assertEqual(self.ResolveDefianceAttack('ally'), (0, 4))

    def test_defiance_preserves_hero_basic_defense_once(self):
        self.assertEqual(self.ResolveDefianceAttack('hero'), (1, 0))

    def test_defiance_establishes_hero_without_basic_defense(self):
        self.assertEqual(self.ResolveDefianceAttack(None), (4, 0))


if __name__ == '__main__':
    unittest.main()
