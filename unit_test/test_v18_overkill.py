from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

# Preserve the application's normal import ordering.
from engine import Engine

from game.card.face.attribute.can_health import CanHealth
from game.element.damage_property import DamageProperty
from game.message import Message


class TookDamageMessage:
    sent = []

    def __init__(self, unit, source, took_damage, by_effect,
                 would_take_damage_message, *, excess_damage):
        self.who_took_damage = unit
        self.took_damage = took_damage
        self.excess_damage = excess_damage
        self.damaged_overkill_target = None

    def Send(self):
        TookDamageMessage.sent.append(self)


class DefeatedMessage:
    sent = []

    def __init__(self, source, unit, took_damage, excess_damage,
                 damaged_overkill_target, by_effect,
                 would_take_damage_message):
        self.who_took_damage = unit
        self.took_damage = took_damage
        self.excess_damage = excess_damage
        self.damaged_overkill_target = damaged_overkill_target

    def Send(self):
        DefeatedMessage.sent.append(self)


class AfterDealDamageMessage:
    sent = []

    def __init__(self, would_deal_damage_message, damage_messages, by_effect):
        self.damage_messages = list(damage_messages)

    def Send(self):
        AfterDealDamageMessage.sent.append(self)


class V18OverkillTests(unittest.TestCase):

    def setUp(self):
        TookDamageMessage.sent = []
        DefeatedMessage.sent = []
        AfterDealDamageMessage.sent = []
        self.message_patches = [
            patch.object(Message, 'AfterUnitTookDamage', TookDamageMessage),
            patch.object(Message, 'AfterUnitDefeatedUnit', DefeatedMessage),
            patch.object(Message, 'AfterFaceDealDamage', AfterDealDamageMessage),
        ]
        for message_patch in self.message_patches:
            message_patch.start()

        self.source = object()
        self.by_effect = object()
        self.attack = SimpleNamespace(
            would_atk_message=SimpleNamespace(has_defeated_target=False),
        )

    def tearDown(self):
        for message_patch in reversed(self.message_patches):
            message_patch.stop()

    def MakeHelper(self, took_damage, excess_damage):
        would_deal = SimpleNamespace(damage=max(1, took_damage))
        would_take = SimpleNamespace(would_deal_damage_message=would_deal)
        lost_message = None
        if took_damage:
            lost_message = SimpleNamespace(value=took_damage)
        return SimpleNamespace(
            lost_message=lost_message,
            excess_damage=excess_damage,
            would_take_damage_message=would_take,
        )

    def MakeUnit(self, helper, *, health, defeated, in_play=True):
        return SimpleNamespace(
            health=health,
            TakeDamageNoDeath=Mock(return_value=helper),
            Death=Mock(return_value=defeated),
            IsInPlay=Mock(return_value=in_play),
        )

    def Resolve(self, primary, overkill_target):
        return CanHealth.TakeDamageWithOverkillTarget(
            primary,
            self.source,
            5,
            self.by_effect,
            self.attack,
            overkill_target,
        )

    def test_excess_damage_is_dealt_only_after_primary_defeat(self):
        order = []
        primary = self.MakeUnit(
            self.MakeHelper(5, 3),
            health=-3,
            defeated=True,
            in_play=False,
        )
        target = self.MakeUnit(
            self.MakeHelper(3, 0),
            health=7,
            defeated=False,
        )
        primary.Death.side_effect = lambda *args: order.append('defeat') or True
        target.TakeDamageNoDeath.side_effect = \
            lambda *args, **kwargs: order.append('overkill') or self.MakeHelper(3, 0)

        messages = self.Resolve(primary, target)

        self.assertEqual(order, ['defeat', 'overkill'])
        self.assertEqual(messages[0].who_took_damage, primary)
        self.assertEqual(messages[0].excess_damage, 3)
        self.assertEqual(messages[0].damaged_overkill_target, target)
        self.assertEqual(messages[1].who_took_damage, target)
        self.assertEqual(messages[1].took_damage, 3)
        damage_property = target.TakeDamageNoDeath.call_args.args[1]
        self.assertIsInstance(damage_property, DamageProperty)
        self.assertEqual(damage_property.damage, 3)
        self.assertTrue(damage_property.is_from_overkill)
        self.assertIs(target.TakeDamageNoDeath.call_args.args[3], self.attack)

    def test_surviving_primary_target_prevents_overkill(self):
        primary = self.MakeUnit(
            self.MakeHelper(2, 0),
            health=1,
            defeated=False,
        )
        target = self.MakeUnit(self.MakeHelper(3, 0), health=7, defeated=False)

        messages = self.Resolve(primary, target)

        primary.Death.assert_not_called()
        target.TakeDamageNoDeath.assert_not_called()
        self.assertEqual(len(messages), 1)
        self.assertIsInstance(messages[0], TookDamageMessage)

    def test_tough_or_full_prevention_on_primary_stops_overkill(self):
        primary = self.MakeUnit(
            self.MakeHelper(0, 3),
            health=2,
            defeated=False,
        )
        target = self.MakeUnit(self.MakeHelper(3, 0), health=7, defeated=False)

        messages = self.Resolve(primary, target)

        primary.Death.assert_not_called()
        target.TakeDamageNoDeath.assert_not_called()
        self.assertEqual(messages, [])
        self.assertEqual(AfterDealDamageMessage.sent[0].damage_messages, [])

    def test_defeat_replacement_prevents_overkill(self):
        primary = self.MakeUnit(
            self.MakeHelper(5, 3),
            health=-3,
            defeated=False,
        )
        target = self.MakeUnit(self.MakeHelper(3, 0), health=7, defeated=False)

        messages = self.Resolve(primary, target)

        primary.Death.assert_called_once()
        target.TakeDamageNoDeath.assert_not_called()
        self.assertEqual(len(messages), 1)
        self.assertIsInstance(messages[0], TookDamageMessage)
        self.assertEqual(messages[0].took_damage, 2)

    def test_damage_cap_that_keeps_primary_alive_prevents_overkill(self):
        primary = self.MakeUnit(
            self.MakeHelper(1, 0),
            health=1,
            defeated=False,
        )
        target = self.MakeUnit(self.MakeHelper(3, 0), health=7, defeated=False)

        self.Resolve(primary, target)

        primary.Death.assert_not_called()
        target.TakeDamageNoDeath.assert_not_called()

    def test_tough_on_overkill_recipient_prevents_only_transferred_damage(self):
        primary = self.MakeUnit(
            self.MakeHelper(5, 3),
            health=-3,
            defeated=True,
            in_play=False,
        )
        target = self.MakeUnit(
            self.MakeHelper(0, 3),
            health=10,
            defeated=False,
        )

        messages = self.Resolve(primary, target)

        target.TakeDamageNoDeath.assert_called_once()
        target.Death.assert_not_called()
        self.assertEqual(len(messages), 1)
        self.assertIsInstance(messages[0], DefeatedMessage)
        self.assertIsNone(messages[0].damaged_overkill_target)


if __name__ == '__main__':
    unittest.main()
