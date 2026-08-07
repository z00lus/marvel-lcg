from types import SimpleNamespace
import importlib
import unittest
from unittest.mock import Mock, patch

# Preserve the application's normal import ordering.
from engine import Engine

from cards.database import CardsDB
from engine.lib.version import Ver
from game.ability.ability_type import AbilityType, TimingPriority
from game.card.factory import CardFactory
from game.card.face.model.face_on_event import ModelOnEvent
from game.message import Message
from game.world.world_rule import WorldRule


class V18DefinedTermsTimingTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        Ver.Initialize()
        if not CardsDB.papers:
            CardsDB.Initialize()

    def MakeRule(self, name: str) -> WorldRule:
        rule = WorldRule()
        rule.SetRule([name], is_puzzle=False, seed=1)
        return rule

    def CreateFace(self, card_id: str, rule: WorldRule):
        world = Mock()
        world.rule = rule
        world.GetPlayerNumIcon.return_value = 1
        return CardFactory.CreateFace(CardsDB.FindCardPaper(card_id), world)

    def test_v18_cards_receive_defined_keyword_scheduler_adapters(self):
        rule = self.MakeRule('v18_all')
        cases = [
            ('01172', 'Retaliate', AbilityType.ForcedResponse),
            ('01167', 'Quickstrike', AbilityType.ForcedResponse),
            ('32159', 'Teamwork', AbilityType.ForcedResponse),
            ('01076', 'Toughness', AbilityType.ForcedResponse),
            ('33005', 'Temporary', AbilityType.ForcedInterrupt),
            ('50083', 'Vulnerable', AbilityType.ForcedInterrupt),
            ('03009', 'Restricted', AbilityType.ForcedResponse),
        ]

        for card_id, name, ability_type in cases:
            with self.subTest(card_id=card_id, name=name):
                face = self.CreateFace(card_id, rule)
                abilities = face.ability.Find(name=name, type=ability_type)
                self.assertEqual(len(abilities), 1)

    def test_retaliate_and_quickstrike_adapters_invoke_keyword_resolution(self):
        rule = self.MakeRule('v18_all')

        retaliate_ability = self.CreateFace('01172', rule).ability.Find(
            name='Retaliate',
            type=AbilityType.ForcedResponse,
        )[0]
        retaliate = Mock()
        retaliate_source = Mock()
        retaliate_source.CastTo.return_value = retaliate
        attack_message = Mock()
        attack_message.would_atk_unit_message = object()
        retaliate_ability.operation(
            SimpleNamespace(this=retaliate_source),
            attack_message,
        )
        retaliate.ResolveRetaliate.assert_called_once_with(
            attack_message.would_atk_unit_message
        )

        quickstrike_ability = self.CreateFace('01167', rule).ability.Find(
            name='Quickstrike',
            type=AbilityType.ForcedResponse,
        )[0]
        quickstrike = Mock()
        quickstrike_source = Mock()
        quickstrike_source.CastTo.return_value = quickstrike
        engage_message = SimpleNamespace(engaged_player=object())
        quickstrike_ability.operation(
            SimpleNamespace(this=quickstrike_source),
            engage_message,
        )
        quickstrike.ResolveQuickstrike.assert_called_once_with(
            engage_message.engaged_player
        )

    def test_toughness_and_temporary_adapters_apply_their_effects(self):
        rule = self.MakeRule('v18_all')
        tough_ability = self.CreateFace('01076', rule).ability.Find(
            name='Toughness',
            type=AbilityType.ForcedResponse,
        )[0]
        temporary_ability = self.CreateFace('33005', rule).ability.Find(
            name='Temporary',
            type=AbilityType.ForcedInterrupt,
        )[0]
        tough_face = Mock()
        temporary_face = Mock()
        tough_effect = SimpleNamespace(this=tough_face)
        temporary_effect = SimpleNamespace(this=temporary_face)

        with patch('game.operate.faces.Faces.GiveStatus') as give_status, \
            patch('game.operate.faces.Faces.DiscardAll') as discard:
            tough_ability.operation(tough_effect, Mock())
            temporary_ability.operation(temporary_effect, Mock())

        give_status.assert_called_once_with([tough_face], 'Tough', tough_effect)
        discard.assert_called_once_with([temporary_face], temporary_effect)

    def test_status_card_scripts_use_status_forced_interrupt_priority(self):
        rule = self.MakeRule('v18_all')

        for module_name in [
            'cards.pack.status.tough',
            'cards.pack.status.stunned',
            'cards.pack.status.confused',
        ]:
            with self.subTest(module=module_name):
                abilities = importlib.import_module(module_name).GetAbilities()
                self.assertTrue(abilities)
                for ability in abilities:
                    self.assertTrue(ability.flags.IsType(AbilityType.Status))
                    self.assertEqual(
                        ability.flags.GetPriority(rule),
                        TimingPriority.Status,
                    )

    def test_tough_and_stunned_statuses_replace_the_matching_resolution(self):
        tough_ability = importlib.import_module(
            'cards.pack.status.tough'
        ).GetAbilities()[0]
        stunned_ability = importlib.import_module(
            'cards.pack.status.stunned'
        ).GetAbilities()[0]

        for ability, discard_method, discard_rule in [
            (tough_ability, 'DiscardTough', 1),
            (stunned_ability, 'DiscardStunned', 'Steady'),
        ]:
            with self.subTest(status=discard_method):
                unit = Mock()
                status = Mock()
                status.GetBindFace.return_value = unit
                source = Mock()
                source.CastTo.return_value = status
                effect = SimpleNamespace(this=source)
                message = Mock()

                ability.operation(effect, message)

                message.SetBeInstead.assert_called_once_with(effect)
                getattr(unit, discard_method).assert_called_once_with(
                    effect,
                    rule=discard_rule,
                )

    def test_v18_reveal_registers_incite_and_surge_as_when_revealed(self):
        rule = self.MakeRule('v18_all')
        registered = []
        registered_effects = []

        def register_temp(ability, **kwargs):
            registered.append(ability)
            effect = Mock(is_unregister=False)
            registered_effects.append(effect)
            return [effect]

        face = SimpleNamespace(
            incite=1,
            surge=1,
            card=SimpleNamespace(world=SimpleNamespace(rule=rule)),
            effect=SimpleNamespace(RegisterTemp=register_temp),
        )
        owner = SimpleNamespace(GetThis=lambda: face)
        reveal_message = SimpleNamespace(cancel_when_revealed=True)
        revealed = SimpleNamespace(reveal_message=reveal_message)

        with patch(
            'game.card.face.attribute.can_incite.CanIncite.IsType',
            return_value=True,
        ), patch(
            'game.card.face.attribute.can_surge.CanSurge.IsType',
            return_value=True,
        ):
            ModelOnEvent.OnWhenCardRevealed(owner, revealed)

        self.assertEqual(
            [(ability.name, ability.type) for ability in registered],
            [
                ('Incite', AbilityType.WhenRevealed),
                ('Surge', AbilityType.WhenRevealed),
            ],
        )
        for effect in registered_effects:
            effect.UnRegisterSelf.assert_called_once_with()

    def test_incite_and_surge_can_be_canceled_as_when_revealed(self):
        def can_cancel(rule_name: str, *, incite: int, surge: int) -> bool:
            rule = self.MakeRule(rule_name)
            face = SimpleNamespace(
                incite=incite,
                surge=surge,
                card=SimpleNamespace(world=SimpleNamespace(rule=rule)),
                effect=SimpleNamespace(Find=lambda **kwargs: []),
            )
            reveal = object.__new__(Message.WhenPlayerRevealCard)
            reveal.private_trigger = face
            reveal.by_effect = object()
            reveal.cannot_be_cancel = False
            reveal.cancel_all_effects = False
            reveal.cancel_when_revealed = False
            check_message = SimpleNamespace(can_be_cancel=True, Send=lambda: None)

            with patch.object(
                Message,
                'CheckIfEffectCanBeCancelBy',
                return_value=check_message,
            ), patch(
                'game.card.face.attribute.can_incite.CanIncite.IsType',
                return_value=bool(incite),
            ), patch(
                'game.card.face.attribute.can_surge.CanSurge.IsType',
                return_value=bool(surge),
            ):
                return Message.WhenPlayerRevealCard.CanBeCancel(
                    reveal,
                    'WhenRevealed',
                    object(),
                )

        self.assertTrue(can_cancel('v18_all', incite=1, surge=0))
        self.assertTrue(can_cancel('v18_all', incite=0, surge=1))


if __name__ == '__main__':
    unittest.main()
