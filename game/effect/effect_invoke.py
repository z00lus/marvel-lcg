from core import *
from build import Build
from game.card.face import *
from game.effect import *
from game.message import *
from game.player import *
from engine.log import Log
from engine.profile import Coverage
from game.world import *

CATEGORY_NAME = "EFFECT"

class EffectInvoker:

    @staticmethod
    def InvokeOperation(effect: 'Effect', message: 'Message2'):
        from game.message import Message
        from game.card.face.base import Unit2
        from game.player import Player
        # from game.operate.faces import Faces

        world = effect.world
        effect.context.ResetBeforeOperation()

        ################################################################################
        try:
            effect.ability.operation(effect, message) # type: ignore
        except Exception as exc:
            # Fix "09004"
            if effect.world.is_game_over:
                pass
            else:
                raise exc

        if Coverage.is_enable:
            Coverage.TrackCallable(effect.ability.operation)

        ################################################################################
        if effect.context.end_attack_messages:
            attacked_targets: List['CardFace'] = []
            damage_targets: List['Unit2'] = []
            atk_messages: List['Message.AfterUnitAttackUnit|Message.AttackEndsBeforeDamageDealt'] = []

            end_atk_message = effect.context.end_attack_messages[0]
            total_dealt_damage = 0
            for message in effect.context.end_attack_messages:
                # assert message.by_effect == end_atk_message.by_effect
                assert message.attacker == end_atk_message.attacker
                # We remove this assert for "09004"
                # assert message.would_atk_message == end_atk_message.would_atk_message
                attacked_targets += message.attacked_targets
                damage_targets += message.damaged_targets
                total_dealt_damage += message.total_dealt_damage
                atk_messages += message.atk_messages

                for message in message.atk_messages:
                    message.Send()

            end_message = Message.AfterUnitAttackEnd(
                end_atk_message.attacker,
                attacked_targets,
                damage_targets,
                total_dealt_damage,
                end_atk_message.by_effect,
                atk_messages,
                end_atk_message.would_atk_messages[0]
            )

            end_message.Send()
            world.stat.RecordAttack(end_message)

        if effect.context.end_thwart_messages:
            schemes: List[Scheme2] = []
            after_thw_messages: List['Message.AfterUnitThwartScheme'] = []
            total_remove_threat = 0

            end_thw_message = effect.context.end_thwart_messages[0]

            for message in effect.context.end_thwart_messages:
                # We remove this assert for "44023"
                # assert message.would_thw_message == end_thw_message.would_thw_message
                schemes += message.schemes
                total_remove_threat += message.total_remove_threat
                after_thw_messages += message.after_thw_messages

            end_message = Message.AfterUnitThwartEnd(
                end_thw_message.trigger,
                schemes,
                total_remove_threat,
                end_thw_message.by_effect,
                after_thw_messages
            )

            end_message.Send()
            world.stat.RecordThwart(end_message)

        # if end_attack_message:
        #     end_attack_message.Send()

        if effect.ability.is_label_defense and \
            isinstance(message, AttackerMessageInternal) and \
            Player.IsType(effect.initiator):
            for would_atk_message in message.would_atk_messages:
                assert would_atk_message.has_resolves_defense_labeled_ability_internal == None or \
                    would_atk_message.has_resolves_defense_labeled_ability_internal == effect.initiator
                would_atk_message.has_resolves_defense_labeled_ability_internal = effect.initiator

    @staticmethod
    def ResolveSelfInternal(effect: 'Effect', message: 'Message2|None', to_player: 'Player|None', by_effect: 'Effect', ref_message: 'Message2|None'=None, *, skip_cost: bool=False) -> bool:
        from game.player import Player
        from game.card.face.attribute.can_defense import CanDefense

        can_action = True

        ability = effect.ability
        initiator = effect.initiator
        world = effect.world
        this = effect.this

        control_by = effect.this.GetControlBy()

        if not skip_cost:
            can_action = effect.ProcessSelfCost()

        if can_action:
            if isinstance(initiator, Player) and to_player == None:
                to_player = initiator

            if ability.flags.is_check_pay:
                pass
            if ability.is_label_defense:
                defender = effect.GetInitiator().GetIdentity()
                if message and CanDefense.IsType(defender):
                    # When a player initiates a triggered ability labeled as
                    # a defense—such as “Hero Interrupt (defense)”—
                    # during an enemy attack, that player’s identity
                    # becomes the defender and is considered to have
                    # defended the attack if there is not already a defender.
                    # if isinstance(message, Send.WhenUnitBeingAttack|Send.WhenUnitWouldAttack):
                    # if message.defender == None:
                    defender.SpecialDefense(message, effect)

        if can_action:
            if effect.is_unregister_after_exec:
                effect.UnRegisterSelf()
            if message and message.send_resolve_message:
                effect.SetHasSpellInPhase()

            from engine import Engine
            controller_manager = Engine.game.controller_manager
            if not Build.release:
                controller_manager.console.TryBreak(world)

            resolve_message = None

            try:
                # invoke_operation
                should_send = False
                if message == None:
                    should_send = True
                if message and message.send_resolve_message and not ability.flags.is_delay_ability and not ability.flags.is_statistics:
                    from game.card.face.card_type import Event
                    from game.card.face.card_type import Resource

                    should_send = True
                    # if Event.IsType(self.this):
                    if ability.is_play and not Event.IsType(this):
                        should_send = False
                    if ability.flags.is_discard_pay and not Resource.IsType(this):
                        should_send = False

                if should_send:
                    resolve_message = Message.WhenEffectWouldResolve(effect, message, by_effect, to_player, control_by)
                    resolve_message.Send()
                    if resolve_message.is_be_instead:
                        return False

                if isinstance(ref_message, ability.when):
                    EffectInvoker.InvokeOperation(effect, ref_message)
                elif isinstance(message, ability.when):
                    EffectInvoker.InvokeOperation(effect, message)
                    if isinstance(message, Message.WhenCardRevealed):
                        message.reveal_message.AddResolved(effect)
                else:
                    assert ability.when in [
                        Message.WhenCardRevealed,
                        Message.WhenUnitBeDefeated,
                        Message.WhenUnitWouldAttack,
                        Message.WhenUnitWouldScheme,
                        Message.AfterUnitAttackEnd,
                        Message.AfterUnitTookDamage,
                        Message.WhenSchemeBeDefeated,
                        Message.WhenResolvePreparationAbility,
                        Message.WhenCardBecomeBoost,
                    ]

                    class ExTriggerPlayerMessage(TriggerNonePlayerMessage):
                        def __init__(self, player: 'Player|None', world: 'World') -> None:
                            self.by_effect = by_effect
                            super().__init__(player, world=world)
                        def GetKillerPlayer(self) -> None:
                            return None
                        def GetAgainstPlayer(self) -> 'Player|None':
                            return self.to_player
                        def GetByPlayer(self) -> 'Player|None':
                            return self.to_player
                        def GetDefeatingPlayer(self) -> 'Player|None':
                            return self.to_player

                    to_player_message = ExTriggerPlayerMessage(to_player, world)
                    EffectInvoker.InvokeOperation(effect, to_player_message)

            except Exception as exc:
                info = Log.OnCrash(CATEGORY_NAME, exc, effect.GetDisplayName(), ability.operation)
                world.render.ErrorOccurred(info)

            if not Build.release:
                controller_manager.console.TryBreak(world)

            send_resolve_message = message and message.send_resolve_message or message == None
            if send_resolve_message and \
                not ability.flags.is_check_pay and \
                ( \
                    ability.flags.is_interrupt or \
                    ability.flags.is_response or \
                    ability.flags.is_resource or \
                    ability.flags.is_when_completed or \
                    ability.flags.is_when_reveal or \
                    ability.flags.is_when_defeated or \
                    ability.flags.is_setup or \
                    ability.flags.is_boost or \
                    ability.flags.is_special or \
                    ability.flags.is_action
                ):
                    if resolve_message != None:
                        after_message = Message.AfterEffectResolved(effect, message, resolve_message)
                        after_message.Send()
            for cost_func in effect.cost_func.GetAll():
                cost_func.AfterCheck(effect)
            effect.cost_func.Reset()
            effect.context.ResetAfterOperation()

        return can_action
