from . import *

from game.message.message_type import HasEndEventMessage
# from game.event.message_type import HasPreEventMessage

class RunAt:

    @staticmethod
    def TheEndOfThePhase(by_effect: 'Effect', operation: Callable[[], Any]):
        by_effect.this.effect.RegisterTemp(
            AbilityFactory.WhenPhaseEnd(
                AbilityType.Temp2,
                None,
                lambda effect, message:
                    operation()
            ),
            unregister_after_exec=True,
        )

    @staticmethod
    def RoundEnd(by_effect: 'Effect', operation: Callable[[], Any]):
        by_effect.this.effect.RegisterTemp(
            AbilityFactory.WhenRoundEnd(
                AbilityType.Temp2,
                None,
                lambda effect, message:
                    operation()
            ),
            unregister_after_exec=True,
        )

    @staticmethod
    def TurnEnd(by_effect: 'Effect', operation: Callable[[], Any]):
        by_effect.this.effect.RegisterTemp(
            AbilityFactory.WhenPlayerTurnEnd(
                AbilityType.Temp2,
                "AnyPlayer",
                lambda effect, message:
                    operation()
            ),
            unregister_after_exec=True,
        )

    # def DoAfterPlay(by_effect: 'Effect', message: 'Send.WhenPlayerPlayCard', operation: Callable[[], Any]):
    #     by_effect.this.effect.RegisterTempEffect(
    #         AbilityFactory.AfterPlayerPlayedCard(
    #             AbilityType.Temp2,
    #             None,
    #             message,
    #             lambda effect, message:
    #                 operation()
    #         )
    #     )

    @staticmethod
    def AfterEventEnd(by_effect: 'Effect',
                      would_message: 'Message.WhenUnitWouldAttack|Message.WhenUnitWouldScheme|Message.WhenUnitWouldThwart|Message.WhenUnitWouldAttackUnit|Message.WhenSchemeBeingThwart|Message.WhenUnitBeingAttack|Message.WhenSchemeBeingScheme|Message.WhenUnitWouldDefend|Message.WhenUnitUseBasicPower|Message.WhenEffectWouldResolve|Message.WhenCardFlip|Message.AfterUnitAttackEnd|Message.AfterUnitDefendEnd|Message.WhenCardWouldMoveToArea|Message.WhenMinionWouldEngagePlayer|None',
                      operation: Callable[[], Any]):
        this = by_effect.this

        # if isinstance(would_message, Message.WhenUnitBeingAttack|Message.WhenSchemeBeingScheme):
        #     would_message = would_message.would_message

        def create_effect_interal(ability: 'Ability', *, is_ally: bool=False):
            this.effect.RegisterTemp(
                ability,
                unregister_after_exec=True
            )

        def create_effect(end_event: Type[TMP], condition: Callable[['Effect', 'TMP'], bool]):
            create_effect_interal(
                Ability(
                    AbilityType.Temp2,
                    end_event,
                    [condition],
                    lambda effect, message:
                        operation()
                )
            )

        if isinstance(would_message, Message.AfterUnitAttackEnd):
            create_effect(
                Message.AfterUnitAttackEnd,
                lambda effect, message:
                    would_message == message,
            )
        elif isinstance(would_message, Message.AfterUnitDefendEnd):
            create_effect(
                Message.AfterUnitDefendEnd,
                lambda effect, message:
                    would_message == message,
            )
        elif isinstance(would_message, Message.WhenUnitWouldAttack):
            create_effect(
                Message.AfterUnitAttackEnd,
                lambda effect, message:
                    would_message in message.would_atk_messages,
            )
        elif isinstance(would_message, Message.WhenUnitWouldScheme):
            create_effect(
                Message.AfterUnitSchemeEnd,
                lambda effect, message:
                    would_message in message.would_sch_messages,
            )
        elif isinstance(would_message, Message.WhenUnitWouldThwart):
            create_effect(
                Message.AfterUnitThwartScheme,
                lambda effect, message:
                    would_message == message.would_thw_message,
            )
        elif isinstance(would_message, Message.WhenUnitWouldAttackUnit):
            create_effect(
                Message.AfterUnitAttackEnd,
                lambda effect, message:
                    would_message.would_atk_message in message.would_atk_messages,
            )
        elif isinstance(would_message, Message.WhenSchemeBeingThwart):
            create_effect(
                Message.AfterUnitThwartEnd,
                lambda effect, message:
                    would_message.would_thw_message in message.would_thw_messages,
            )
        elif isinstance(would_message, Message.WhenUnitBeingAttack):
            create_effect(
                Message.AfterUnitAttackEnd,
                lambda effect, message:
                    would_message.would_atk_message in message.would_atk_messages,
            )
        elif isinstance(would_message, Message.WhenSchemeBeingScheme):
            create_effect(
                Message.AfterUnitSchemeEnd,
                lambda effect, message:
                    would_message.would_sch_message in message.would_sch_messages,
            )
        elif isinstance(would_message, Message.WhenUnitWouldDefend):
            create_effect(
                Message.AfterUnitDefendEnd,
                lambda effect, message:
                    would_message in message.would_def_messages,
            )
        elif isinstance(would_message, Message.WhenUnitUseBasicPower):
            create_effect(
                Message.AfterUnitUseBasicPower,
                lambda effect, message:
                    would_message == message.pre_message,
            )
        elif isinstance(would_message, Message.WhenEffectWouldResolve):
            create_effect(
                Message.AfterEffectResolved,
                lambda effect, message:
                    would_message == message.pre_message,
            )
        elif isinstance(would_message, Message.WhenCardFlip):
            create_effect(
                Message.AfterCardFlip,
                lambda effect, message:
                    would_message == message.pre_message,
            )
        elif isinstance(would_message, Message.WhenCardWouldMoveToArea): # TODO: add end event?
            create_effect(
                Message.AfterCardsMoved,
                lambda effect, message:
                    would_message.trigger in message.faces,
            )
        elif isinstance(would_message, Message.WhenMinionWouldEngagePlayer):
            create_effect(
                Message.AfterMinionEngagePlayer,
                lambda effect, message:
                    would_message.trigger == message.trigger,
            )
        else:
            assert False

    @staticmethod
    def AfterEnemyActivationEnd(by_effect: 'Effect', would_message: 'Message.WhenUnitWouldScheme|Message.WhenUnitWouldAttack|Message.WhenUnitBeingAttack|Message.WhenSchemeBeingScheme', operation: Callable[[], Any]):
        if isinstance(would_message, Message.WhenUnitBeingAttack|Message.WhenSchemeBeingScheme):
            would_message = would_message.would_message

        def is_this_message(effect: 'Effect', message: 'Message.AfterEnemyActivationEnd'):
            if message.atk_message:
                if would_message in message.atk_message.would_atk_messages:
                    return True
            if message.sch_message:
                if would_message in message.sch_message.would_sch_messages:
                    return True
            return False

        def operation_fn():
            # Fix "44014" make "45159" attack with boost "45152"
            operation()
            # assert would_message.property.against_player
            # would_message.property.against_player.ChooseAbilities(
            #     by_effect,
            #     AbilityFactory.ForChoiceAbility(
            #         "",
            #         lambda targets:
            #             operation()
            #     )
            # )

        by_effect.this.effect.RegisterTemp(
            AbilityFactory.AfterEnemyActivationEnd(
                AbilityType.Temp2,
                None,
                lambda effect, message:
                    operation_fn(),
                conditions=[is_this_message],
            ),
            unregister_after_exec=True,
        )

    @staticmethod
    def AfterResolveEffect(by_effect: 'Effect', check_effect: 'Effect', operation: Callable[[], Any]):
        by_effect.this.effect.RegisterTemp(
            AbilityFactory.AfterCardResolveAbility(
                AbilityType.Temp2,
                None,
                None,
                lambda effect, message:
                    operation(),
                which_effect=check_effect
            ),
            unregister_after_exec=True,
        )

    @staticmethod
    def AfterResolveMessage(by_effect: 'Effect', check_message: 'HasEndEventMessage|Message.WhenUnitWouldAttack', operation: Callable[[], Any]):
        if isinstance(check_message, Message.WhenUnitWouldAttack):
            by_effect.this.effect.RegisterTemp(
                AbilityFactory.AfterUnitAttackEnd(
                    AbilityType.Temp2,
                    None,
                    lambda effect, message:
                        operation(),
                    would_atk_message=check_message
                ),
                unregister_after_exec=True,
            )
        else:
            by_effect.this.effect.RegisterTemp(
                Ability(
                    AbilityType.Temp2,
                    check_message.end_event,
                    [
                        lambda effect, message:
                            # isinstance(message, HasPreEventMessage) and \
                            message.pre_message == check_message,
                    ],
                    lambda effect, message:
                        operation(),
                ),
                unregister_after_exec=True,
            )

    @staticmethod
    def AfterFaceEnterPlay(by_effect: 'Effect', face: 'CardFace', operation: Callable[[], Any]):
        by_effect.this.effect.RegisterTemp(
            AbilityFactory.AfterCardEnterPlay(
                AbilityType.Temp2,
                face,
                lambda effect, message:
                    operation()
            ),
            unregister_after_exec=True,
        )

    @staticmethod
    def AfterPowerUsed(by_effect: 'Effect', message: 'Message.WhenUnitUseBasicPower', operation: Callable[[], Any]):
        by_effect.this.effect.RegisterTemp(
            AbilityFactory.AfterUnitUseBasicPower(
                AbilityType.Temp2,
                None,
                lambda effect, message:
                    operation(),
                use_message=message
            ),
            unregister_after_exec=True,
            until_event_end=message
        )

    # @staticmethod
    # def NextVillainPhaseBegin(by_effect: 'Effect', operation: Callable[[], Any]):
    #     round_id = by_effect.world.round_id + 1
    #     # if not by_effect.world.phase.IsVillainPhase():
    #     #     round_id -= 1
    #     by_effect.this.effect.RegisterTempEffect(
    #         AbilityFactory.WhenPhaseBegin(
    #             AbilityType.Temp2,
    #             "Villain",
    #             lambda effect, message:
    #                 operation(),
    #             round_id=round_id,
    #         ),
    #         unregister_after_exec=True,
    #     )

    @staticmethod
    def WhenCardSetup(face: 'CardFace', operation: Callable[[], Any]):
        face.effect.RegisterTemp(
            AbilityFactory.WhenCardSetup(
                face,
                lambda effect, message:
                    operation()
            ),
            unregister_after_exec=True,
        )

    @staticmethod
    def WhenGameBeginSetup(face: 'CardFace', operation: Callable[[], Any]):
        face.effect.RegisterTemp(
            AbilityFactory.WhenGameBeginSetup(
                lambda effect, message:
                    operation()
            ),
            unregister_after_exec=True,
        )
