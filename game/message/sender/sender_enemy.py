from . import *
from typing import Final

class SenderEnemy:

    ################################################################################
    # Villain and Minion
    ################################################################################
    # No `CanBeInstead`
    class WhenVillainWouldAdvance(TriggerUnitMessage):
        def __init__(self, unit: 'Villain') -> None:
            super().__init__(trigger=unit)
            text = TransText("{unit} would advance", unit=unit)
            self.Present(text, "", unit)

    class WhenVillainAdvance(TriggerUnitMessage, HasEndEventMessage):
        def __init__(self, unit: 'Villain', by_effect: 'Effect') -> None:
            from game.message import Message
            super().__init__(trigger=unit, end_event=Message.AfterVillainAdvanced)

    class AfterVillainAdvanced(TriggerUnitMessage, HasPreEventMessage):
        def __init__(self, unit: 'Villain', by_effect: 'Effect', message: 'Message.WhenVillainAdvance') -> None:
            super().__init__(trigger=unit, pre_message=message)
            text = TransText("{unit} advanced", unit=unit)
            self.Present(text, "set", unit)

    class WhenMinionWouldEngagePlayer(TriggerUnitMessage, HasEndEventMessage, CanBeInstead):
        def __init__(self, unit: 'Minion', player: 'Player', by_effect: 'Effect') -> None:
            from game.message import Message
            self.player: Final = player
            self.by_effect: Final = by_effect
            self.minion: Final = unit
            self.would_engaged_player: Final = player
            super().__init__(trigger=unit, player=player, end_event=Message.WhenMinionEngagePlayer)

        @property
        def engaged_message(self) -> 'Message.WhenMinionEngagePlayer':
            return self.next_message

    class WhenMinionEngagePlayer(TriggerUnitMessage, HasPreEventMessage, HasEndEventMessage):
        def __init__(self, would_message: 'Message.WhenMinionWouldEngagePlayer') -> None:
            from game.message import Message
            self.player: Final = would_message.would_engaged_player
            self.by_effect: Final = would_message.by_effect
            self.minion: Final = would_message.minion
            super().__init__(trigger=self.minion, player=self.player, pre_message=would_message, end_event=Message.AfterMinionEngagePlayer)
            text = TransText("{unit} is engaging {player} ({by_effect})", unit=self.minion, player=self.player, by_effect=self.by_effect.this)
            self.Present(text, "", self.minion, self.player.GetIdentity(), self.by_effect.this)

        @property
        def engaged_player(self) -> 'Player':
            return self.player

    class AfterMinionEngagePlayer(TriggerUnitMessage, TriggerPlayerMessage, HasPreEventMessage):
        def __init__(self, unit: 'Minion', player: 'Player', message: 'Message.WhenMinionEngagePlayer') -> None:
            self.player: Final = player
            super().__init__(trigger=unit, player=player, pre_message=message)
            text = TransText("{unit} engaged {player}", unit=unit, player=player)
            self.Present(text, "", unit)

        @property
        def engaged_player(self) -> 'Player':
            return self.player

    class WhenEnemyWouldBeGivenBoostCard(TriggerUnitMessage, CanBeInstead):
        def __init__(self, unit: 'Minion|Villain', boost_card: 'CardFace', by_effect: 'Effect', would_message: 'Message.WhenUnitWouldAttack|Message.WhenUnitWouldScheme|None') -> None:
            self.boost_card: Final = boost_card
            self.by_effect: Final = by_effect
            self.would_message: Final = would_message
            super().__init__(trigger=unit)

    class AfterEnemyGivenBoostCard(TriggerUnitMessage, AttackerNoneOldMessage):
        def __init__(self, unit: 'Minion|Villain', boost_card: 'CardFace', by_effect: 'Effect', would_message: 'Message.WhenUnitWouldAttack|Message.WhenUnitWouldScheme|None') -> None:
            from game.message import Message
            self.boost_card: Final = boost_card
            self.by_effect: Final = by_effect
            self.trigger_attacker: Final = unit
            self.would_atk_message: Final = would_message if isinstance(would_message, Message.WhenUnitWouldAttack) else None
            attacker = self.would_atk_message.attacker if self.would_atk_message else None
            attacked = self.would_atk_message.attacker if self.would_atk_message else None
            super().__init__(trigger=unit, attacker=attacker, attacked=[attacked], would_atk_message=self.would_atk_message)
            text = TransText("{unit} gains {face} as boost card ({by_effect})", unit=unit, face=boost_card, by_effect=by_effect.this)
            self.Present(text, "", by_effect.this)

        def GetAttacker(self) -> 'Minion|Villain':
            assert self.would_atk_message != None
            return self.trigger_attacker

    class AfterUnitGainFaceDownBoostCards_Text(TextMessage):
        def __init__(self, unit: 'Minion|Villain', size: int, by_effect: 'Effect') -> None:
            super().__init__(world=by_effect.world)
            # if size:
            #     text = TransText("{unit} gains {size} boost card(s) ({by_effect})", unit=unit, size=size, by_effect=by_effect.this)
            #     self.Present(text, "set", by_effect.this)

    class WhenEnemyWouldActivate(TriggerUnitMessage, TriggerNonePlayerMessage, CanBeInstead):
        def __init__(self, unit: 'Enemy', player: 'Player') -> None:
            self.power: Literal["SCH", "ATK"] = "SCH" if player.IsAlterEgo() else "ATK"
            super().__init__(trigger=unit, player=player)

        def GiveBoostCardForThisActivation(self, num: int, by_effect: 'Effect'):
            from game.ability.ability import AbilityType
            from game.ability.factory import AbilityFactory
            self.trigger.effect.RegisterTemp(
                AbilityFactory.WhenEnemyActivateAgainstYou(
                    AbilityType.Temp0,
                    "This",
                    lambda effect, message:
                        message.GiveAdditionalBoostCardForThisActivation(num, by_effect),
                    conditions=[
                        lambda effect, message:
                            self == message.would_act_message
                    ]
                ),
                unregister_after_exec=True,
                until_phase_end=True,
            )

    class WhenEnemyActivateAgainstYou(TriggerUnitMessage, TriggerNonePlayerMessage, HasEndEventMessage):
        def __init__(self, unit: 'Enemy', player: 'Player|None', by_effect: 'Effect', would_message: 'Message.WhenUnitWouldScheme|Message.WhenUnitWouldAttack', would_act_message: 'Message.WhenEnemyWouldActivate|None') -> None:
            from game.message import Message
            self.by_effect: Final = by_effect
            self.would_message: Final = would_message
            self.would_act_message: Final = would_act_message
            super().__init__(trigger=unit, player=player, end_event=Message.AfterEnemyActivationEnd)
            if player:
                text = TransText("{unit} would activate against {player}", unit=unit, player=player)
                self.Present(text, "", unit, player.GetIdentity())
            else:
                text = TransText("{unit} would activate", unit=unit, player=player)
                self.Present(text, "", unit)

        def GiveAdditionalBoostCardForThisActivation(self, num: int, by_effect: 'Effect'):
            #  If a boost ability on a boost card dealt to a minion refers to “the villain,” that ability still applies to the villain (even though a minion is resolving it).
            from game.card.face.attribute.can_boost import CanBoost
            if CanBoost.IsType(self.trigger):
                self.trigger.GiveFacedownBoostCardsInternal(num, by_effect, self.would_message)

    class AfterEnemyActivationEnd(TriggerUnitMessage, TriggerNonePlayerMessage, HasPreEventMessage):
        def __init__(self, unit: 'Enemy', message: 'Message.AfterUnitAttackEnd|Message.AfterUnitSchemeEnd', activate_message: 'Message.WhenEnemyActivateAgainstYou') -> None:
            from game.message import Message
            assert message
            is_scheme = type(message) is Message.AfterUnitSchemeEnd
            self.atk_message: Final = None if is_scheme else message.CastTo(Message.AfterUnitAttackEnd)
            self.sch_message: Final = message.CastTo(Message.AfterUnitSchemeEnd) if is_scheme else None
            self.active_message: Final = message

            super().__init__(trigger=unit, player=activate_message.to_player, pre_message=activate_message)
            self.AddRelatedFace(unit.card.face) # Fix "39013b"
            text = TransText("{unit} activation ends", unit=unit)
            if unit.IsInPlay():
                self.Present(text, "", unit)
            else:
                self.Present(text, "")

        def HasThisBoost(self, face: 'CardFace') -> bool:
            boost_faces: List['CardFace'] = []
            if self.atk_message:
                for message in self.atk_message.atk_messages:
                    boost_faces += message.boost_faces
            if self.sch_message:
                boost_faces += self.sch_message.boost_cards
            return face in boost_faces

        @property
        def activate_message(self) -> 'Message.WhenEnemyActivateAgainstYou':
            return self.pre_message

        # def GetAgainstPlayerSafe(self) -> 'Player|None':
        #     if self.activate_message.IsToPlayer():
        #         return self.activate_message.GetToPlayer()
        #     else:
        #         return None

        def GetAgainstPlayer(self) -> 'Player':
            return self.activate_message.GetToPlayer()

        # @override
        # def GetToPlayer(self) -> 'Player':
        #     assert False

    ################################################################################
    # Scheme
    class GettingEnemySchemeTarget(TriggerUnitMessage, GettingMessage):
        def __init__(self, unit: 'Unit2', by_effect: 'Effect') -> None:
            self.who_scheme: Final = unit
            self.by_effect: Final = by_effect
            self.target_scheme = None
            super().__init__(unit)
            self.AddRelatedFace(unit, by_effect)

        def SetSchemeTarget(self, target_scheme: 'Scheme2', by_effect: 'Effect'):
            self.target_scheme = target_scheme

    class WhenUnitWouldScheme(TriggerUnitMessage, SchemerMessage, CanGainValueMessage, CanBeInstead):
        def __init__(self, unit: 'Unit2', by_effect: 'Effect', *, property: 'SchemeProperty') -> None:
            self.property: Final = property
            self.by_effect: Final = by_effect
            self.remove_threat_instead_of_placing: Effect|None = None
            if self.property.additional_value and self.IsBasicScheme():
                value = self.property.additional_value
                self.property.additional_value = 0
                unit.GainForThisActive(by_effect, self, scheme=value)
            super().__init__(trigger=unit, schemer=unit)
            text = TransText("{unit} will scheme ({additional_value:+}) ({by_effect})", unit=unit, additional_value=property.additional_value, by_effect=by_effect)
            self.Present(text, "", unit)

        def GainSCHForThisScheme(self, value: int, by_effect: 'Effect'):
            from game.card.face.base import Enemy
            enemy = self.trigger.CastTo(Enemy)
            enemy.GainForThisActive(by_effect, self, scheme=value)

        # Call `CheckEnemySchemeTarget`
        # def ChangeSchemeTarget(self, scheme: 'Scheme2', by_effect: 'Effect'):
        #     self.ReplaceTarget(scheme)

        def IsBasicScheme(self):
            return self.property.is_basic_power

        def SetRemoveThreatInsteadOfPlacing(self, by_effect: 'Effect'):
            self.remove_threat_instead_of_placing = by_effect

        def GetAgainstPlayer(self) -> 'Player|None':
            return self.against_player

        @property
        def against_player(self) -> 'Player|None':
            return self.property.against_player

        def DoNotGiveBoostCardForThisActivation(self, by_effect: 'Effect'):
            self.property.do_not_give_boost = True

        def GiveAdditionalBoostCardForThisActivation(self, num: int, by_effect: 'Effect'):
            from game.ability.ability import AbilityType
            from game.ability.factory import AbilityFactory
            self.trigger.effect.RegisterTemp(
                AbilityFactory.WhenEnemyActivateAgainstYou(
                    AbilityType.Temp0,
                    "This",
                    lambda effect, message:
                        message.GiveAdditionalBoostCardForThisActivation(num, by_effect),
                    conditions=[
                        lambda effect, message:
                            self == message.would_message
                    ]
                ),
                unregister_after_exec=True,
                until_phase_end=True,
            )

        # @property
        # def target_scheme(self) -> 'Scheme2':
        #     from game.card.face.base import Scheme2
        #     assert len(self.schemed_targets) == 1
        #     assert Scheme2.IsType(self.schemed_targets[0])
        #     return self.schemed_targets[0]

    class WhenSchemeBeingScheme(TriggerUnitMessage, HasEndEventMessage, CanGainValueMessage):
        def __init__(self, scheme: 'Scheme2', would_sch_message: 'Message.WhenUnitWouldScheme') -> None:
            from game.message import Message
            # self.trigger: Final = unit # attacker
            self.scheme: Final = scheme
            self.property = would_sch_message.property
            self.would_sch_message: Final = would_sch_message
            self.would_message: Final = would_sch_message
            self.by_face: Final = would_sch_message.trigger
            # Render.Print(f'{unit} thwarted {scheme}, value {value}', unit, scheme)
            super().__init__(trigger=would_sch_message.trigger, end_event=Message.AfterUnitThwartScheme)

        def IsAttack(self) -> bool:
            return False

        def IsScheme(self) -> bool:
            return True

    class WhenRecalculateSchemeValue(CalculateMessage, TriggerUnitMessage):
        def __init__(self, unit: 'Unit2', target: 'Scheme2', value: int, would_sch_message: 'Message.WhenUnitWouldScheme') -> None:
            self.scheme: Final = target
            self.would_sch_message: Final = would_sch_message
            self.value = value
            super().__init__(trigger=unit)

        def UpdateSchemeValue(self, value: int):
            self.value += value

    class AfterUnitSchemeEnd(TriggerUnitMessage):
        def __init__(self, unit: 'Unit2', threat: int, target: 'Scheme2', boost_faces: Sequence['CardFace'], by_effect: 'Effect', would_sch_messages: List['Message.WhenUnitWouldScheme']) -> None:
            self.placed_threat: Final = threat
            self.boost_cards: Final = boost_faces
            self.by_effect: Final = by_effect
            self.would_sch_messages: Final = would_sch_messages
            self.target_scheme: Final = target
            super().__init__(trigger=unit)

        def GetAgainstPlayer(self) -> 'Player|None':
            return self.against_player

        @property
        def against_player(self) -> 'Player|None':
            if len(self.would_sch_messages) == 1:
                return self.would_sch_messages[0].against_player
            return None
