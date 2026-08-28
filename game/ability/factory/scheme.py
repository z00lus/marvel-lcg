from . import *

class AbilityFactoryScheme:

    @staticmethod
    def WhenThreatWouldBePlacedOn(ability_type: 'AbilityType',
                                   which_scheme: CardType,
                                   operation: OperationType[Message.WhenSchemeWouldPlaceThreat],
                                   *,
                                   by_scheme: 'Message.WhenUnitWouldScheme|None'=None,
                                   conditions: ConditionsType[Message.WhenSchemeWouldPlaceThreat]=[],
                                   ) -> 'Ability':
        return AbilityFactoryScheme.WhenSchemeWouldPlaceThreat(
            ability_type,
            which_scheme,
            operation,
            by_scheme=by_scheme,
            conditions=conditions
        )

    @staticmethod
    def WhenSchemeWouldPlaceThreat(ability_type: 'AbilityType',
                                   which_scheme: CardType,
                                   operation: OperationType[Message.WhenSchemeWouldPlaceThreat],
                                   *,
                                   by_scheme: 'Message.WhenUnitWouldScheme|None'=None,
                                   conditions: ConditionsType[Message.WhenSchemeWouldPlaceThreat]=[],
                                   ) -> 'Ability':

        def check_which_scheme(effect: 'Effect', message: 'Message.WhenSchemeWouldPlaceThreat') -> bool:
            return Condition.CheckWhichCard(which_scheme, message.trigger, effect)

        def check_by_scheme(effect: 'Effect', message: 'Message.WhenSchemeWouldPlaceThreat') -> bool:
            if not by_scheme:
                return True
            return by_scheme == message.sch_message

        return Ability(
            ability_type,
            Message.WhenSchemeWouldPlaceThreat,
            [
                lambda effect, message:
                    message.value > 0,
                check_which_scheme,
                check_by_scheme,
                *conditions
            ],
            operation,
            is_local=which_scheme == "This"
        )

    @staticmethod
    def WhenSchemeWouldRemoveThreat(ability_type: 'AbilityType',
                                   which_scheme: CardType,
                                   operation: OperationType[Message.WhenSchemeWouldRemoveThreat],
                                   *,
                                   who_make_thwart: CardType=None,
                                   thwart_event: 'Message.WhenUnitWouldThwart|None'=None,
                                   conditions: ConditionsType[Message.WhenSchemeWouldRemoveThreat]=[],
                                   ) -> 'Ability':

        def check_which_scheme(effect: 'Effect', message: 'Message.WhenSchemeWouldRemoveThreat') -> bool:
            return Condition.CheckWhichCard(which_scheme, message.trigger, effect)

        def check_who_make_thwart(effect: 'Effect', message: 'Message.WhenSchemeWouldRemoveThreat') -> bool:
            return Condition.CheckWhichCard(who_make_thwart, message.by_effect.this, effect)

        def check_thwart_event(effect: 'Effect', message: 'Message.WhenSchemeWouldRemoveThreat') -> bool:
            if thwart_event == None:
                return True
            return thwart_event == message.would_thw_message

        return Ability(
            ability_type,
            Message.WhenSchemeWouldRemoveThreat,
            [
                lambda effect, message:
                    message.value > 0,
                check_which_scheme,
                check_who_make_thwart,
                check_thwart_event,
                *conditions
            ],
            operation,
            is_local=which_scheme == "This"
        )

    @staticmethod
    def AfterSchemePlaceThreat(ability_type: 'AbilityType',
                               which_scheme: CardType,
                               operation: OperationType[Message.AfterSchemePlaceThreat],
                               *,
                               has_at_least_threat: int|Literal["5*"]|Callable[['Effect'], int]|None=None,
                               conditions: ConditionsType[Message.AfterSchemePlaceThreat]=[],
                               ) -> 'Ability':
        from game.card.face.base import Scheme2
        from game.operate.worlds import Worlds

        def check_which_scheme(effect: 'Effect', message: 'Message.AfterSchemePlaceThreat'):
            return Condition.CheckWhichCard(which_scheme, message.trigger, effect)

        def check_has_threat(effect: 'Effect', message: 'Message.AfterSchemePlaceThreat') -> bool:
            if has_at_least_threat == None:
                return True
            if isinstance(has_at_least_threat, int):
                check_threat = has_at_least_threat
            elif isinstance(has_at_least_threat, str):
                check_threat = Worlds.ConvertPerPlayerIconToInt(has_at_least_threat, effect)
            else:
                check_threat = has_at_least_threat(effect)
            return effect.this.CastTo(Scheme2).threat >= check_threat

        return Ability(
            ability_type,
            Message.AfterSchemePlaceThreat,
            [
                check_which_scheme,
                check_has_threat,
                *conditions
            ],
            operation,
            is_local=which_scheme == "This"
        )

    @staticmethod
    def AfterSchemeRemoveThreat(ability_type: 'AbilityType',
                                which_scheme: CardType,
                                operation: OperationType[Message.AfterSchemeRemoveThreat],
                                *,
                                by_who: CardType|Literal["You"]=None,
                                by_thwart: 'bool|Message.WhenUnitWouldThwart|None'=None,
                                last_threat: bool|None=None,
                                conditions: ConditionsType[Message.AfterSchemeRemoveThreat]=[],
                                ) -> 'Ability':
        from game.card.face.base import Scheme2

        def check_which_scheme(effect: 'Effect', message: 'Message.AfterSchemeRemoveThreat') -> bool:
            return Condition.CheckWhichCard(which_scheme, message.trigger, effect)

        def check_by_who(effect: 'Effect', message: 'Message.AfterSchemeRemoveThreat') -> bool:
            if by_who == None:
                return True
            you_rule = Condition.GetYouRule(by_who, identity=True)
            return Condition.CheckWhichCard(
                you_rule,
                message.would_remove_message.by_face,
                effect,
            )

        def check_by_thwart(effect: 'Effect', message: 'Message.AfterSchemeRemoveThreat') -> bool:
            if by_thwart == None:
                return True
            if isinstance(by_thwart, bool):
                if by_thwart:
                    return message.would_thw_message != None
                else:
                    return message.would_thw_message == None
            return message.would_thw_message == by_thwart

        def check_last_threat(effect: 'Effect', message: 'Message.AfterSchemeRemoveThreat') -> bool:
            if last_threat == None:
                return True
            return message.trigger.CastTo(Scheme2).threat == 0

        return Ability(
            ability_type,
            Message.AfterSchemeRemoveThreat,
            [
                check_which_scheme,
                check_by_who,
                check_by_thwart,
                check_last_threat,
                *conditions
            ],
            operation,
            is_local=which_scheme == "This"
        )

    @staticmethod
    def AfterUnitDefeatSchemeInternal(ability_type: 'AbilityType',
                                    which_scheme: CardType,
                                    operation: OperationType[Message.AfterUnitDefeatedScheme],
                                    *,
                                    who_make_thwart: CardType|Literal["You"]=None,
                                    conditions: ConditionsType[Message.AfterUnitDefeatedScheme]=[],
                                    ) -> 'Ability':

        def check_which_scheme(effect: 'Effect', message: 'Message.AfterUnitDefeatedScheme') -> bool:
            return Condition.CheckWhichCard(which_scheme, message.scheme, effect)

        def check_who_make_thwart(effect: 'Effect', message: 'Message.AfterUnitDefeatedScheme') -> bool:
            you_rule = Condition.GetYouRule(who_make_thwart, identity=True)
            return Condition.CheckWhichCard(you_rule, message.trigger, effect)

        return Ability(
            ability_type,
            Message.AfterUnitDefeatedScheme,
            [
                check_which_scheme,
                check_who_make_thwart,
                *conditions
            ],
            operation,
            is_local=who_make_thwart == "This" or which_scheme == "This"
        )

    @staticmethod
    def AfterUnitDefeatedScheme(ability_type: 'AbilityType',
                               who_make_thwart: CardType|Literal["You"],
                               which_scheme: CardType,
                               operation: OperationType[Message.AfterUnitDefeatedScheme],
                               *,
                               conditions: ConditionsType[Message.AfterUnitDefeatedScheme]=[],
                               is_from_thwart: bool|None=None
                               ) -> 'Ability':
        from game.ability.factory import AbilityFactory
        def action(effect: 'Effect', message: 'Message.WhenUnitWouldThwart|Message.WhenSchemeWouldRemoveThreat') -> None:
            this = effect.this
            ability = AbilityFactoryScheme.AfterUnitDefeatSchemeInternal(
                ability_type,
                which_scheme,
                operation,
                who_make_thwart=who_make_thwart,
                conditions=conditions
            )
            ability.CopyFromDelayEffect(effect)
            this.effect.RegisterTemp(
                ability,
                unregister_after_exec=True,
                until_event_end=message,
                # phase_end=True
            )
            # Bug: LimitOncePerPhase
            
        if is_from_thwart:
            return AbilityFactory.WhenUnitWouldThwart(
                AbilityType.DelayAbility,
                who_make_thwart,
                action,
                thwarted_scheme=which_scheme,
            )
        else:
            return AbilityFactory.AfterUnitDefeatSchemeInternal(
                ability_type,
                which_scheme,
                operation,
                who_make_thwart=who_make_thwart,
                conditions=conditions
            )

    @staticmethod
    def AfterSchemeBeDefeated(ability_type: 'AbilityType',
                              which_scheme: CardType,
                              operation: OperationType[Message.AfterSchemeBeDefeated],
                              *,
                              conditions: ConditionsType[Message.AfterSchemeBeDefeated]=[],
                              ) -> 'Ability':

        def check_which_scheme(effect: 'Effect', message: 'Message.AfterSchemeBeDefeated') -> bool:
            return Condition.CheckWhichCard(which_scheme, message.trigger, effect)

        return Ability(
            ability_type,
            Message.AfterSchemeBeDefeated,
            [
                check_which_scheme,
                *conditions
            ],
            operation,
            is_local=which_scheme == "This"
        )

    @staticmethod
    def WhenMainSchemeStageWouldBeCompleted(ability_type: 'AbilityType',
                                            which_scheme: CardType,
                                            operation: OperationType[Message.WhenMainSchemeStageWouldBeCompleted]) -> 'Ability':
        # When a main scheme is complete, all "When Completed" abilities on the card resolve.
        def check_which_scheme(effect: 'Effect', message: 'Message.WhenMainSchemeStageWouldBeCompleted') -> bool:
            return Condition.CheckWhichCard(which_scheme, message.trigger, effect)

        return Ability(
            ability_type,
            Message.WhenMainSchemeStageWouldBeCompleted,
            [check_which_scheme],
            operation,
            is_local=which_scheme == "This"
        )

    # WhenThisSchemeStageCompleted
    @staticmethod
    def WhenMainSchemeStageCompleted(ability_type: 'AbilityType',
                                     which_scheme: CardType,
                                     operation: OperationType[Message.WhenMainSchemeStageCompleted]) -> 'Ability':
        # When a main scheme is complete, all "When Completed" abilities on the card resolve.
        def check_which_scheme(effect: 'Effect', message: 'Message.WhenMainSchemeStageCompleted') -> bool:
            return Condition.CheckWhichCard(which_scheme, message.trigger, effect)

        return Ability(
            ability_type,
            Message.WhenMainSchemeStageCompleted,
            [check_which_scheme],
            operation,
            is_local=which_scheme == "This"
        )

    @staticmethod
    def AfterMainSchemeCompleted(ability_type: 'AbilityType',
                                 which_scheme: CardType,
                                 operation: OperationType[Message.AfterMainSchemeCompleted]) -> 'Ability':
        def check_which_scheme(effect: 'Effect', message: 'Message.AfterMainSchemeCompleted') -> bool:
            return Condition.CheckWhichCard(which_scheme, message.trigger, effect)

        return Ability(
            ability_type,
            Message.AfterMainSchemeCompleted,
            [check_which_scheme],
            operation,
            is_local=which_scheme == "This"
        ).NoOutOfPlayLimit()

    @staticmethod
    def WhenLastThreatRemoveFromThisScheme(ability_type: 'AbilityType',
                                           operation: OperationType[Message.AfterCardRemovedToken],
                                           *,
                                           conditions: ConditionsType[Message.AfterCardRemovedToken]=[],
                                           ) -> 'Ability':
        from game.card.face.base import Scheme2

        return Ability(
            ability_type,
            Message.AfterCardRemovedToken,
            [
                Condition2.ThisIsTrigger,
                lambda effect, message:
                    message.token_name == 'threat' and \
                    Scheme2.IsType(effect.this) and \
                    effect.this.threat == 0,
                *conditions
            ],
            operation,
            is_local=True
        )

    @staticmethod
    def AfterLastThreatIsRemovedFromHere(ability_type: 'AbilityType',
                                        operation: OperationType[Message.AfterCardRemovedToken],
                                        *,
                                        conditions: ConditionsType[Message.AfterCardRemovedToken]=[],
                                        ) -> 'Ability':
        return AbilityFactoryScheme.WhenLastThreatRemoveFromThisScheme(
            ability_type,
            operation,
            conditions=conditions
        )

    @staticmethod
    def WhenCalcThisSchemeEscalation(operation: Callable[['Effect'], int]) -> 'Ability':
        def calc_scheme_escalation(effect: 'Effect', message: 'Message.CalcMainSchemeEscalation') -> None:
            message.escalation_threat += operation(effect)

        return Ability(
            AbilityType.NonKeyword,
            Message.CalcMainSchemeEscalation,
            [
                Condition2.ThisIsTrigger,
            ],
            calc_scheme_escalation
        )

    @staticmethod
    def WhenCalcThisSchemeTargetThreat(operation: Callable[['Effect'], int]) -> 'Ability':
        def calc_scheme_escalation(effect: 'Effect', message: 'Message.CalcMainSchemeEscalation') -> None:
            message.escalation_threat += operation(effect)

        return Ability(
            AbilityType.NonKeyword,
            Message.CalcMainSchemeEscalation,
            [
                Condition2.ThisIsTrigger,
            ],
            calc_scheme_escalation,
            is_local=True
        )

    @staticmethod
    # Can skip adding this for the last main scheme
    def IfThisSchemeStageIsCompletedPlayersLoseTheGame() -> 'Ability':
        # return AbilityFactory.WhenThisSchemeComplete(
        #     lambda effect, message:
        #         World().PlayersEndTheGame(False)
        # )
        return Ability(
            AbilityType.NonKeyword,
            Message.WhenMainSchemeStageCompleted,
            [
                Condition2.ThisIsTrigger,
            ],
            lambda effect, message:
                effect.world.game_over.SetGameOver("The Main Scheme was Completed", effect),
            is_local=True
        )

    @staticmethod
    def IfNoThreatHerePlayersWinTheGame() -> 'Ability':
        from game.ability.factory import AbilityFactory
        from game.operate.worlds import Worlds

        return AbilityFactory.WhenLastThreatRemoveFromThisScheme(
            AbilityType.NonKeywordBold,
            lambda effect, message:
                Worlds.SetGameOver(True, effect)
        )

    ################################################################################
    # Cannot remove threat
    @staticmethod
    def ThreatCannotBeRemovedFromWhile(from_where: CardType=None,
                                       *,
                                        # from_card_name: str|None=None,
                                        by_thwarting: bool|None=None,
                                        by_character: 'CardFinder|None'=None,
                                        conditions: ConditionsType[Message.WhenSchemeWouldRemoveThreat]=[],
                                        while_face_is_in_play: 'CardFinder|None'=None,
                                        not_from_this_effect: bool=False
                                        ) -> 'Ability':
        from game.operate.worlds import Worlds

        def cannot_be_removed(effect: 'Effect', message: 'Message.WhenSchemeWouldRemoveThreat') -> None:
            message.SetCannotBeRemoved(effect)

        def check_from_where(effect: 'Effect', message: 'Message.WhenSchemeWouldRemoveThreat') -> bool:
            return Condition.CheckWhichCard(from_where, message.trigger, effect)

        # def check_card_name(effect: 'Effect', message: 'Send.WhenSchemeWouldRemoveThreat') -> bool:
        #     if from_card_name == None:
        #         return True
        #     return message.trigger.IsName(from_card_name)

        def check_from_thwart(effect: 'Effect', message: 'Message.WhenSchemeWouldRemoveThreat') -> bool:
            if by_thwarting == None:
                return True
            if by_thwarting:
                return message.would_thw_message != None
            else:
                return message.would_thw_message == None

        def check_by_character(effect: 'Effect', message: 'Message.WhenSchemeWouldRemoveThreat') -> bool:
            if by_character == None:
                return True
            return by_character.Check(message.by_face)

        def check_while_who_is_in_play(effect: 'Effect', message: 'Message.WhenSchemeWouldRemoveThreat') -> bool:
            if while_face_is_in_play == None:
                return True
            for face in Worlds.GetOnFieldCards(effect):
                if while_face_is_in_play.Check(face):
                    return True
            return False

        def check_not_from_this_effect(effect: 'Effect', message: 'Message.WhenSchemeWouldRemoveThreat') -> bool:
            if not_from_this_effect:
                return effect.this != message.trigger
            return True

        return Ability(
            AbilityType.NonKeyword,
            Message.WhenSchemeWouldRemoveThreat,
            [
                check_from_where,
                # check_card_name,
                check_from_thwart,
                check_while_who_is_in_play,
                check_not_from_this_effect,
                check_by_character,
                *conditions
            ],
            cannot_be_removed,
            is_local=from_where == "This"
        )

    ################################################################################
    #
    @staticmethod
    def WhenMainSchemeWouldAdvance(ability_type: 'AbilityType',
                                    which_scheme: CardType,
                                    operation: OperationType[Message.WhenMainSchemeWouldAdvance],
                                    *,
                                    stage: int|None=None,
                                    conditions: ConditionsType[Message.WhenMainSchemeWouldAdvance]=[],
                                    ) -> 'Ability':

        def check_which_scheme(effect: 'Effect', message: 'Message.WhenMainSchemeWouldAdvance'):
            return Condition.CheckWhichCard(which_scheme, message.trigger, effect)

        def check_stage(effect: 'Effect', message: 'Message.WhenMainSchemeWouldAdvance'):
            if stage == None:
                return True
            return message.scheme.printed_stage == stage

        return Ability(
            ability_type,
            Message.WhenMainSchemeWouldAdvance,
            [
                check_which_scheme,
                check_stage,
                *conditions
            ],
            operation,
            is_local=which_scheme == "This"
        )

    ################################################################################
    #
    @staticmethod
    def IfThereIsAtLeastThreatHere(at_least: Callable[['Effect'], int]|int|Literal["4*"],
                                    operation: OperationType[Message.AfterCardPlacedToken],
                                    *,
                                    conditions: ConditionsType[Message.AfterCardPlacedToken]=[],
                                    ) -> 'Ability':
        from game.ability.factory import AbilityFactory
        return AbilityFactory.AfterCardPlacedToken(
            AbilityType.NonKeyword,
            "This",
            'threat',
            operation,
            at_least=at_least,
            conditions=conditions
        )

    @staticmethod
    def WhenThreatIsRemovedFrom(ability_type: 'AbilityType',
                                which_scheme: CardType,
                                operation: OperationType[Message.AfterCardRemovedToken],
                                *,
                                conditions: ConditionsType[Message.AfterCardRemovedToken]=[],
                                ) -> 'Ability':
        from game.card.face.base import Scheme2

        def check_which_scheme(effect: 'Effect', message: 'Message.AfterCardRemovedToken'):
            return Condition.CheckWhichCard(which_scheme, message.trigger, effect)

        return Ability(
            ability_type,
            Message.AfterCardRemovedToken,
            [
                Condition2.ThisIsTrigger,
                check_which_scheme,
                lambda effect, message:
                    message.token_name == 'threat' and \
                    Scheme2.IsType(effect.this),
                *conditions
            ],
            operation,
            is_local=True
        )
