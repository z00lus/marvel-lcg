from . import *

class AbilityFactoryThwart:

    @staticmethod
    def WhenUnitThwartScheme(ability_type: 'AbilityType',
                            who_make_thwart: CardType,
                            operation: OperationType[Message.WhenSchemeBeingThwart],
                            *,
                            which_card_be_thwart: CardType=None,
                            is_basic_thwart: bool|None=None,
                            conditions: ConditionsType[Message.WhenSchemeBeingThwart]=[]
                            ) -> 'Ability':

        def check_who_make_thwart(effect: 'Effect', message: 'Message.WhenSchemeBeingThwart') -> bool:
            return Condition.CheckWhichCard(who_make_thwart, message.trigger, effect)

        def check_which_card_be_thwart(effect: 'Effect', message: 'Message.WhenSchemeBeingThwart') -> bool:
            return Condition.CheckWhichCard(which_card_be_thwart, message.scheme, effect)

        def check_is_basic_thwart(effect: 'Effect', message: 'Message.WhenSchemeBeingThwart') -> bool:
            if is_basic_thwart == None:
                return True
            return is_basic_thwart == message.IsBasicThwart()

        return Ability(
            ability_type,
            Message.WhenSchemeBeingThwart,
            [
                check_which_card_be_thwart,
                check_is_basic_thwart,
                check_who_make_thwart,
                *conditions
            ],
            operation,
            is_local=who_make_thwart == "This" or which_card_be_thwart == "This"
        )

    @staticmethod
    def WhenUnitWouldThwart(ability_type: 'AbilityType',
                            who_make_thwart: CardType|Literal["You"],
                            operation: OperationType[Message.WhenUnitWouldThwart],
                            *,
                            thwarted_scheme: CardType=None,
                            is_basic_thwart: bool|None=None,
                            conditions: ConditionsType[Message.WhenUnitWouldThwart]=[]
                            ) -> 'Ability':

        return AbilityFactoryThwart.WhenUnitMakeThwart(
            ability_type,
            who_make_thwart,
            operation=operation,
            against_scheme=thwarted_scheme,
            is_basic_thwart=is_basic_thwart,
            conditions=conditions
        )

    @staticmethod
    def WhenUnitMakeThwart(ability_type: 'AbilityType',
                           who_make_thwart: CardType|Literal["You"],
                           against_scheme: CardType,
                           operation: OperationType[Message.WhenUnitWouldThwart],
                           *,
                           is_basic_thwart: bool|None=None,
                           conditions: ConditionsType[Message.WhenUnitWouldThwart]=[],
                           ) -> 'Ability':

        def check_who_make_thwart(effect: 'Effect', message: 'Message.WhenUnitWouldThwart') -> bool:
            rule = Condition.GetYouRule(who_make_thwart, identity=True)
            return Condition.CheckWhichCard(rule, message.trigger, effect)

        def check_which_card_be_thwart(effect: 'Effect', message: 'Message.WhenUnitWouldThwart') -> bool:
            return Condition.CheckWhichCard(against_scheme, message.schemes, effect)

        def check_is_basic_thwart(effect: 'Effect', message: 'Message.WhenUnitWouldThwart') -> bool:
            if is_basic_thwart == None:
                return True
            return is_basic_thwart == message.IsBasicThwart()

        return Ability(
            ability_type,
            Message.WhenUnitWouldThwart,
            [
                check_who_make_thwart,
                check_which_card_be_thwart,
                check_is_basic_thwart,
                *conditions
            ],
            operation,
            is_local=who_make_thwart == "This" or against_scheme == "This"
        )

    @staticmethod
    def AfterUnitThwartScheme(ability_type: 'AbilityType',
                            who_thwart: CardType,
                            target_scheme: CardType,
                            operation: OperationType[Message.AfterUnitThwartScheme],
                            *,
                            remove_threat: bool|None=None,
                            # remove_all_threat: bool|None=None, # remove_the_last_threat
                            is_basic_thwart: bool|None=None,
                            conditions: ConditionsType[Message.AfterUnitThwartScheme]=[],
                            ) -> 'Ability':

        def check_who(effect: 'Effect', message: 'Message.AfterUnitThwartScheme') -> bool:
            return Condition.CheckWhichCard(who_thwart, message.trigger, effect)

        def check_target_scheme(effect: 'Effect', message: 'Message.AfterUnitThwartScheme') -> bool:
            return Condition.CheckWhichCard(target_scheme, message.scheme, effect)

        def check_remove_threat(effect: 'Effect', message: 'Message.AfterUnitThwartScheme') -> bool:
            if remove_threat == None:
                return True
            return message.remove_threat > 0

        # def check_remove_all_threat_from(effect: 'Effect', message: 'Message.AfterUnitThwartScheme') -> bool:
        #     if remove_all_threat == None:
        #         return True
        #     return message.scheme.threat == 0

        def check_is_basic_thwart(effect: 'Effect', message: 'Message.AfterUnitThwartScheme') -> bool:
            if is_basic_thwart == None:
                return True
            return is_basic_thwart == message.IsBasicThwart()

        return Ability(
            ability_type,
            Message.AfterUnitThwartScheme,
            [
                check_who,
                check_target_scheme,
                check_remove_threat,
                check_is_basic_thwart,
                # check_remove_all_threat_from,
                *conditions
            ],
            operation,
            is_local=who_thwart == "This" or target_scheme == "This"
        )

    @staticmethod
    def AfterUnitMakeThwart(ability_type: 'AbilityType',
                            who_thwart: CardType|Literal["You"],
                            operation: OperationType[Message.AfterUnitThwartEnd],
                            *,
                            is_basic_thwart: bool|None=None,
                            ) -> 'Ability':

        return AbilityFactoryThwart.AfterUnitThwartEnd(
            ability_type,
            who_thwart,
            operation,
            is_basic_thwart=is_basic_thwart,
        )

    @staticmethod
    def AfterUnitThwartAndRemoveLastThreat(ability_type: 'AbilityType',
                                        who_thwart: CardType|Literal["You"],
                                        operation: OperationType[Message.AfterUnitThwartEnd],
                                        *,
                                        is_basic_thwart: bool|None=None,
                                        conditions: ConditionsType[Message.AfterUnitThwartEnd]=[],
                                        ) -> 'Ability':

        def check_remove_all_threat_from(effect: 'Effect', message: 'Message.AfterUnitThwartEnd') -> bool:
            return message.remove_the_last_threat

        return AbilityFactoryThwart.AfterUnitThwartEnd(
            ability_type,
            who_thwart,
            operation,
            is_basic_thwart=is_basic_thwart,
            conditions=[
                check_remove_all_threat_from,
                *conditions
            ]
        )

    @staticmethod
    def AfterUnitThwartEnd(ability_type: 'AbilityType',
                          who_thwart: CardType|Literal["You"],
                          operation: OperationType[Message.AfterUnitThwartEnd],
                          *,
                          is_basic_thwart: bool|None=None,
                          conditions: ConditionsType[Message.AfterUnitThwartEnd]=[],
                          ) -> 'Ability':

        def check_who(effect: 'Effect', message: 'Message.AfterUnitThwartEnd') -> bool:
            rule = Condition.GetYouRule(who_thwart, identity=True)
            return Condition.CheckWhichCard(rule, message.trigger, effect)

        def check_is_basic_thwart(effect: 'Effect', message: 'Message.AfterUnitThwartEnd') -> bool:
            if is_basic_thwart == None:
                return True
            return is_basic_thwart == message.IsBasicThwart()

        return Ability(
            ability_type,
            Message.AfterUnitThwartEnd,
            [
                check_who,
                check_is_basic_thwart,
                *conditions
            ],
            operation,
            is_local=who_thwart == "This"
        )

    @staticmethod
    def UnitCannotThwartTarget(who_thwart: CardType,
                               *,
                               cannot_thwart: CardType|Literal[True]=None,
                               can_only_thwart: CardType=None,
                               cannot_trigger_thwart_ability: bool|None=None,
                               conditions: ConditionsType[Message.CheckIfSchemeCanBeThwartBy]=[],
                               ) -> List['Ability']:
        from game.ability.factory import AbilityFactory

        if cannot_thwart == True:
            abilities = [
                Ability(
                    AbilityType.NonKeyword,
                    Message.CheckIfUnitCanThwart,
                    [
                        lambda effect, message:
                            Condition.CheckWhichCard(who_thwart, message.check_unit, effect),
                        # *conditions,
                    ],
                    lambda effect, message:
                        message.SetCannotThwart(effect),
                    is_local=who_thwart == "This"
                )
            ]
        else:
            def check_who_thwart(effect: 'Effect', message: 'Message.CheckIfSchemeCanBeThwartBy') -> bool:
                return Condition.CheckWhichCard(who_thwart, message.who_thwart, effect)

            def check_which_scheme(effect: 'Effect', message: 'Message.CheckIfSchemeCanBeThwartBy') -> bool:
                if cannot_thwart == True:
                    return True
                return Condition.CheckWhichCard(cannot_thwart, message.scheme, effect)

            def check_can_only_thwart(effect: 'Effect', message: 'Message.CheckIfSchemeCanBeThwartBy') -> bool:
                if can_only_thwart == None:
                    return True
                return not Condition.CheckWhichCard(can_only_thwart, message.scheme, effect)

            abilities = [
                Ability(
                    AbilityType.NonKeyword,
                    Message.CheckIfSchemeCanBeThwartBy,
                    [
                        check_who_thwart,
                        check_which_scheme,
                        check_can_only_thwart,
                        *conditions
                    ],
                    lambda effect, message:
                        message.SetCannotBeThwart(effect),
                    # A "can only thwart this scheme" restriction must inspect
                    # attempts against every scheme, not only messages already
                    # related to this card.  The allowed target may be local;
                    # the restriction itself is global.
                    is_local=who_thwart == "This" or cannot_thwart == "This"
                )
            ]

        if who_thwart == "AttachedIdentity" and cannot_trigger_thwart_ability != False:
            abilities.append(
                AbilityFactory.PlayersCannotTriggerAbility(
                    "AttachedPlayer",
                    None,
                    label='thwart',
                )
            )

        return abilities
