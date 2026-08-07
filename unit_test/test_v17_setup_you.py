from types import SimpleNamespace
import inspect
import unittest
from unittest.mock import Mock, patch

# Preserve the application's normal import ordering.
from engine import Engine

from game.ability.ability import Ability
from game.ability.ability_type import AbilityType
from game.ability.condition.card_type import ConditionCardType
from game.card.face.base.card_encounter import EncounterNonVillainCard
from game.card.face.card_face import CardFace
from game.card.face.card_type.identity import Hero
from game.card.face.card_type.resource import Resource
from game.effect.effect import Effect
from game.message import Message
from game.selector.factory import Select
from game.world.world import World
from game.world.world_rule import WorldRule


class V17SetupAndYouTests(unittest.TestCase):

    def test_resource_card_attack_is_performed_by_the_identity(self):
        identity = Mock()
        identity.IsDefeated.return_value = False
        player = SimpleNamespace(GetIdentity=lambda: identity)
        effect = SimpleNamespace(
            world=SimpleNamespace(rule=SimpleNamespace(v17_setup_elimination_you=True)),
            GetInitiator=lambda: player,
        )
        resource = object.__new__(Resource)
        targets = [object()]
        attack_property = object()

        result = Resource.OnDealDamage(
            resource,
            targets,
            3,
            effect,
            property=attack_property,
            attack_in_event=True,
        )

        identity.OnDealDamage.assert_called_once_with(
            targets,
            3,
            effect,
            property=attack_property,
            attack_in_event=True,
        )
        self.assertIs(result, identity.OnDealDamage.return_value)

    def test_resource_card_thwart_is_performed_by_the_identity(self):
        identity = Mock()
        player = SimpleNamespace(GetIdentity=lambda: identity)
        effect = SimpleNamespace(
            world=SimpleNamespace(rule=SimpleNamespace(v17_setup_elimination_you=True)),
            GetInitiator=lambda: player,
        )
        resource = object.__new__(Resource)
        schemes = [object()]

        result = Resource.OnRemoveSchemeThreat(resource, schemes, 2, effect)

        identity.OnRemoveSchemeThreat.assert_called_once_with(schemes, 2, effect)
        self.assertIs(result, identity.OnRemoveSchemeThreat.return_value)

    def test_resource_card_defense_uses_the_identity_for_eligibility(self):
        resource = object.__new__(Resource)
        identity = object.__new__(Hero)
        attacker = object()
        identity.IsCanDefense = Mock(return_value=True)
        player = SimpleNamespace(GetIdentity=lambda: identity)
        effect = SimpleNamespace(
            this=resource,
            world=SimpleNamespace(rule=SimpleNamespace(v17_setup_elimination_you=True)),
            GetInitiator=lambda: player,
        )
        message = object.__new__(Message.WhenUnitWouldAttack)
        message.attacker_internal = attacker
        ability = Ability(
            AbilityType.HeroInterrupt,
            Message.WhenUnitWouldAttack,
            [],
            lambda effect, message: None,
        ).SetLabel('defense')
        with patch('game.card.face.base.Enemy.IsType', return_value=False), \
            patch('game.card.face.card_type.Event.IsType', return_value=False), \
            patch('game.card.face.card_type.Resource.IsType', return_value=True):
            ability.Initialize(resource)
            self.assertTrue(ability.conditions[0](effect, message))
        identity.IsCanDefense.assert_called_once_with(attacker)

    def test_resource_trigger_counts_as_your_identity_but_encounter_and_player_side_scheme_do_not(self):
        identity = object.__new__(CardFace)
        player = SimpleNamespace(
            IsPlayer=lambda: True,
            GetIdentity=lambda: identity,
        )
        flags = SimpleNamespace(is_obligations_area=False)
        source = SimpleNamespace(card=SimpleNamespace(area=SimpleNamespace(flags=flags)))
        initiator = SimpleNamespace(IsScenario=lambda: False)
        effect = SimpleNamespace(
            this=source,
            initiator=initiator,
            world=SimpleNamespace(rule=SimpleNamespace(v17_setup_elimination_you=True)),
            context=SimpleNamespace(ask_player=player),
        )

        resource = object.__new__(Resource)
        resource.GetControlByOrOwner = lambda: player
        encounter = object.__new__(CardFace)
        encounter.GetControlByOrOwner = lambda: player
        player_side_scheme = object.__new__(CardFace)
        player_side_scheme.GetControlByOrOwner = lambda: player
        identity.GetControlByOrOwner = lambda: player

        with patch('game.card.face.card_type.Resource.IsType', side_effect=lambda face: face is resource), \
            patch('game.card.face.card_type.Identity.IsType', side_effect=lambda face: face is identity), \
            patch('game.player.Player.IsType', side_effect=lambda value: value is player), \
            patch.object(Select, 'GetYou', return_value=player):
            self.assertTrue(ConditionCardType.CheckWhichCard('YourIdentity', resource, effect))
            self.assertFalse(ConditionCardType.CheckWhichCard('YourIdentity', encounter, effect))
            self.assertFalse(ConditionCardType.CheckWhichCard('YourIdentity', player_side_scheme, effect))

    def test_designated_nemesis_minion_is_deterministic_when_set_has_multiple_minions(self):
        identity = SimpleNamespace(paper=SimpleNamespace(set_name='Test Hero'))
        player = SimpleNamespace(GetIdentity=lambda: identity)
        designated = SimpleNamespace(
            paper=SimpleNamespace(set_name='Test Hero Nemesis'),
            nemesis='Test Hero',
        )
        other_minion = SimpleNamespace(
            paper=SimpleNamespace(set_name='Test Hero Nemesis'),
            nemesis='',
        )

        with patch('game.card.face.card_type.Minion.IsType', return_value=True):
            self.assertTrue(EncounterNonVillainCard.IsNemesis(designated, player))
            self.assertFalse(EncounterNonVillainCard.IsNemesis(other_minion, player))

    def test_repeated_you_references_stay_bound_to_the_same_solo_player(self):
        player = object()
        effect = SimpleNamespace(
            context=SimpleNamespace(ask_player=player),
            this=SimpleNamespace(IsInPlay=lambda: True),
            initiator=object(),
        )

        first = Select.GetYou(effect)
        effect.initiator = object()
        second = Select.GetYou(effect)

        self.assertIs(first, player)
        self.assertIs(second, player)

    def test_v18_encounter_card_abilities_ignore_crisis(self):
        rule = WorldRule()
        rule.SetRule(['v18_all'], is_puzzle=False, seed=1)
        encounter_controller = SimpleNamespace(IsScenario=lambda: True)
        encounter = SimpleNamespace(GetControlByOrOwner=lambda: encounter_controller)
        effect = SimpleNamespace(
            is_rule=False,
            world=SimpleNamespace(rule=rule),
            this=encounter,
        )

        self.assertTrue(Effect.IsIgnoreKeyword(effect, 'Crisis', effect))

    def test_setup_pipeline_keeps_official_solo_order(self):
        source = inspect.getsource(World.Initialize)
        ordered_markers = [
            'scheme.Setup(False)',
            'scheme.Advance(None, game_start_effect)',
            'villain.Setup(False)',
            'villain.Reveal(None, game_start_effect)',
            'Message.WhenCampaignSetup(self)',
            'player.DrawUp("Max", game_start_effect)',
            'player.phase.ResolveMulligans',
            'player.GetIdentity().Setup(False)',
        ]

        positions = [source.index(marker) for marker in ordered_markers]
        self.assertEqual(positions, sorted(positions))


if __name__ == '__main__':
    unittest.main()
