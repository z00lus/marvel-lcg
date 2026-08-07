from typing import TypeAlias
from core import *

from game.card.face import *
from game.effect import *

class ConditionCardType:

    @staticmethod
    def TargetCanBeConfused(effect: 'Effect', target: 'CardFace') -> bool:
        from game.card.face.base import Unit2
        return Unit2.IsType(target) and target.CanbeConfused()

    @staticmethod
    def TargetCanBeStunned(effect: 'Effect', target: 'CardFace') -> bool:
        from game.card.face.base import Unit2
        return Unit2.IsType(target) and target.CanbeStunned()

    @staticmethod
    def TargetCanTakeDamage(effect: 'Effect', target: 'CardFace') -> bool:
        from game.buff import BuffCannotTakeDamage
        from game.card.face.base import Unit2
        return bool(
            Unit2.IsType(target) and
            not target.IsDefeated() and
            not target.GetBuff(BuffCannotTakeDamage)
        )

    SINGLE_CARD_TYPE = Literal[
        "This",
        "ThisFace",
        "YouPlayer",
        "Character",
        "Player",
    ]

    CARD_TYPE_PREFIX = Literal[
        "Another",
        "YouControl",
        # "Your",
        # "Attached",
        # "Engaged",
        # "Attacking",
    ]

    CARD_TYPE_EX = Literal[
        "AnotherScheme",
        "AnotherFriend",
        "YourHero",
        "YourIdentity",
        "YourAlly",
        "YouControlAlly",
        "YouControlCharacter",
        "AttachedIdentity",
        "AttachedCard",
        "AttachedHero",
        "AttachedAlly",
        "AttachedEnemy",
        "AttachedMinion",
        "AttachedVillain",
        "AttachedScheme",
        "AttachedCharacter",
        "AttachedSideScheme",
        "AttachedLeader",
        "EngagedIdentity",
        "EngagedMinion",
        "AttackingEnemy",
        "EnemyLeader",
    ]

    CARD_TYPE: TypeAlias = "Tuple[CARD_TYPE_PREFIX, 'CardFinder'] | CARD_TYPE_EX | SINGLE_CARD_TYPE | Type['CardFace']|None|Sequence['CardFace']|CardFace|CardFinder"

    CARD_TYPE_MIN: TypeAlias = 'Literal["YourIdentity", "EngagedIdentity", "EngagedMinion"]|Type[CardFace]|Literal["This", "Character", "Player"]|None|CardFinder'

    @staticmethod
    def GetYouRule(check_rule: 'CARD_TYPE|Literal["You"]', *, identity: bool) -> 'CARD_TYPE':
        if check_rule != "You":
            return check_rule
        if identity:
            return "YourIdentity"
        else:
            return "YouPlayer"

    @staticmethod
    def CheckWhichCard(check_rule_param: 'CARD_TYPE', check_faces: Sequence['CardFace']|'CardFace|None', from_effect: 'Effect', check_status: bool=False, size: int|Literal["1*"]=1) -> bool:
        from game.card.face.card_face import CardFace
        from game.card.face.card_type import Hero
        from game.card.face.card_type import Ally
        from game.card.face.card_type import Identity
        from game.card.face.card_type import Minion
        from game.card.face.card_type import Attachment
        from game.card.face.card_type import Upgrade
        from game.card.face.card_type import Leader
        from game.card.face.attribute.can_attach import CanAttach
        from game.card.card_finder import CardFinder
        from game.card.face.base import Villain
        from game.card.face.base import Enemy
        from game.card.face.base import Unit2
        from game.card.face.base import SchemeSide2
        from game.card.face.base import Scheme2
        from game.card.face.base import Friend
        from game.player import Player
        from game.ability.condition import Condition
        from game.operate.referential import Referential
        from game.operate.worlds import Worlds
        from game.selector import Select

        def is_sequence_of_card_face(x: Any) -> TypeGuard[Sequence['CardFace']]:
            if not isinstance(x, list):
                return False
            element: Any
            for element in x:
                if not isinstance(element, CardFace):
                    return False
            return True

        def invoke_check_card(check_rule: 'ConditionCardType.CARD_TYPE', face: 'CardFace') -> bool:
            if check_rule == None:
                return True
            if isinstance(check_rule, CardFinder):
                if check_rule:
                    return Referential.Check(check_rule, face, from_effect)
                else:
                    return True
            if isinstance(check_rule, CardFace):
                if check_status:
                    return check_rule.card == face.card
                else:
                    return check_rule == face
            # Sequence['CardFace']
            if is_sequence_of_card_face(check_rule):
                return face in check_rule

            # ONE_CARD_TYPE
            if check_rule == "This":
                return from_effect.this.card == face.card
            if check_rule == "ThisFace":
                return from_effect.this == face
            if check_rule == "YouPlayer":
                return Condition.ThisIsYou(from_effect, face)
            if check_rule == "Character":
                return Unit2.IsType(face)
            if check_rule == "Player":
                return Player.IsType(face.GetControlByOrOwner())

            def check_you(check_face: 'CardFace'=face):
                if from_effect.this.card.area.flags.is_obligations_area:
                    return check_face == from_effect.this.GetBindFace()
                elif from_effect.initiator.IsScenario():
                    return Player.IsType(check_face.GetControlByOrOwner())
                else:
                    return Select.GetYou(from_effect) == check_face.GetControlByOrOwner()
            def check_another():
                # Fix "53008"
                if Upgrade.IsType(from_effect.this) or Attachment.IsType(from_effect.this):
                    return from_effect.this.bind_face != face
                else:
                    return from_effect.this != face
            def check_attached():
                return Condition.ThisAttachedTo(from_effect, face)
            def check_engaged():
                if Minion.IsType(from_effect.this):
                    player = from_effect.this.GetEngagedPlayer()
                    return player == face.GetControlByOrOwner()

                player = None
                if Attachment.IsType(from_effect.this):
                    player = from_effect.this.GetBindFace().GetControlByOrOwner()
                if Identity.IsType(from_effect.this):
                    player = from_effect.this.GetControlByPlayer()
                if isinstance(player, Player):
                    return Minion.IsType(face) and face.engaged_player == player # Fix for "45134" 
                else:
                    return False
            def check_attacking():
                from game.message.message_type import AttackerMessageInternal
                if isinstance(from_effect.bind_message, AttackerMessageInternal):
                    return face == from_effect.bind_message.attacker
                else:
                    return False

            if check_rule == "AnotherScheme":
                return check_another() and Scheme2.IsType(face)
            if check_rule == "AnotherFriend":
                return check_another() and Friend.IsType(face)
            if check_rule == "YourHero":
                return check_you() and Hero.IsType(face)
            if check_rule == "YourIdentity":
                check_face = face
                from game.card.face.card_type import Resource
                if Resource.IsType(face):
                    controller = face.GetControlByOrOwner()
                    if Player.IsType(controller):
                        check_face = controller.GetIdentity()
                return check_you(check_face) and Identity.IsType(check_face)
            if check_rule == "YourAlly":
                return check_you() and Ally.IsType(face)
            if check_rule == "YouControlAlly":
                return check_you() and Ally.IsType(face)
            if check_rule == "YouControlCharacter":
                return check_you() and Unit2.IsType(face)
            if check_rule == "AttachedIdentity":
                return check_attached() and Identity.IsType(face)
            if check_rule == "AttachedCard":
                return check_attached() and CardFace.IsType(face)
            if check_rule == "AttachedHero":
                return check_attached() and Hero.IsType(face)
            if check_rule == "AttachedAlly":
                return check_attached() and Ally.IsType(face)
            if check_rule == "AttachedEnemy":
                return check_attached() and Enemy.IsType(face)
            if check_rule == "AttachedMinion":
                return check_attached() and Minion.IsType(face)
            if check_rule == "AttachedVillain":
                if not check_attached():
                    return False
                # Fix "53038"
                if CanAttach.IsType(from_effect.this) and from_effect.this.is_refers_to_the_villain_refers_to_attached:
                    return from_effect.this.GetBindFace() == face
                else:
                    return Villain.IsType(face)
            if check_rule == "AttachedScheme":
                return check_attached() and Scheme2.IsType(face)
            if check_rule == "AttachedCharacter":
                return check_attached() and Unit2.IsType(face)
            if check_rule == "AttachedSideScheme":
                return check_attached() and SchemeSide2.IsType(face)
            if check_rule == "AttachedLeader":
                return check_attached() and Leader.IsType(face)
            if check_rule == "EngagedIdentity":
                return check_engaged() and Identity.IsType(face)
            if check_rule == "EngagedMinion":
                return check_engaged() and Minion.IsType(face)
            if check_rule == "AttackingEnemy":
                return check_attacking() and Enemy.IsType(face)
            if check_rule == "EnemyLeader":
                # TODO: Add Enemy
                return Leader.IsType(face)

            if isinstance(check_rule, tuple) and \
                not isinstance(check_rule, str):
                ex_prefix, ex_finder = check_rule

                def check_ex_rule():
                    assert not isinstance(ex_prefix, CardFace)
                    if ex_prefix == "Another":
                        return check_another()
                    if ex_prefix == "YouControl" or ex_prefix == "Your":
                        return check_you()
                    if ex_prefix == "Attached":
                        return check_attached()
                    if ex_prefix == "Engaged":
                        return check_engaged()
                    if ex_prefix == "Attacking":
                        return check_attacking()
                    assert False

                if not check_ex_rule():
                    return False
                if ex_finder == "Character":
                    return Unit2.IsType(face)
                assert not isinstance(ex_finder, CardFace)

                # if ex_prefix == "Attached":
                #     if CanAttach.IsType(from_effect.this) and \
                #         from_effect.this.is_refers_to_the_villain_refers_to_attached and \
                #         ex_finder == Villain:
                #         return True

                # if isinstance(ex_type, CardFinder):
                return ex_finder.Check(face)

            assert not isinstance(check_rule, Sequence)

            # Fix "53038"
            if CanAttach.IsType(from_effect.this) and \
                from_effect.this.is_refers_to_the_villain_refers_to_attached and \
                check_rule == Villain:
                return True
            return check_rule.IsType(face)

        if check_rule_param == None:
            return True
        if check_faces == None:
            return False
        if isinstance(check_faces, CardFace):
            assert size == 1
            return invoke_check_card(check_rule_param, check_faces)

        checked = 0
        if isinstance(size, str):
            size = Worlds.ConvertPerPlayerIconToInt(size, from_effect)
        for face in check_faces:
            if invoke_check_card(check_rule_param, face):
                checked += 1
            if checked >= size:
                return True
        return False
