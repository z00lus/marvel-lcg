from . import *

class AbilityFactoryBoost:

    @staticmethod
    def WhenCardBecomeBoost(which_card: CardType,
                            operation: OperationType[Message.WhenCardBecomeBoost],
                            *,
                            during_scheme: bool=False,
                            during_attack: bool=False,
                            is_undefended_attack: bool|None=None,
                            attacker: Type['TC']|None=None,
                            activating_enemy: CardType=None,
                            you_are_in_hero_from: bool|None=None,
                            conditions: ConditionsType[Message.WhenCardBecomeBoost]=[],
                            ) -> 'Ability':

        def check_which_card(effect: 'Effect', message: 'Message.WhenCardBecomeBoost') -> bool:
            return Condition.CheckWhichCard(which_card, message.trigger, effect)

        def check_undefended_attack(effect: 'Effect', message: 'Message.WhenCardBecomeBoost') -> bool:
            if is_undefended_attack != None:
                if not isinstance(message.being_message, Message.WhenUnitBeingAttack):
                    return False
                return is_undefended_attack == (message.being_message.would_atk_message.GetDefender() == None)
            return True

        def check_attacker(effect: 'Effect', message: 'Message.WhenCardBecomeBoost') -> bool:
            if attacker:
                if not isinstance(message.being_message, Message.WhenUnitBeingAttack):
                    return False
                if not message.being_message.attacker:
                    return False
                return attacker.IsType(message.being_message.attacker)
            return True

        def check_activating_enemy(effect: 'Effect', message: 'Message.WhenCardBecomeBoost') -> bool:
            return Condition.CheckWhichCard(activating_enemy, message.activating_enemy, effect)

        def check_you_are_in_hero_from(effect: 'Effect', message: 'Message.WhenCardBecomeBoost') -> bool:
            if you_are_in_hero_from != None:
                player = message.GetToPlayer()
                if you_are_in_hero_from:
                    return player.IsHero()
                else:
                    return not player.IsHero()
            return True

        return Ability(
            AbilityType.Boost,
            Message.WhenCardBecomeBoost,
            [
                lambda effect, message:
                    not message.is_cancel_boost_ability,
                check_which_card,
                check_undefended_attack,
                check_attacker,
                check_activating_enemy,
                lambda effect, message:
                    ( not during_attack or message.being_message.IsAttack() ) and \
                    ( not during_scheme or message.being_message.IsScheme() ),
                check_you_are_in_hero_from,
                *conditions
            ],
            operation,
            is_local=which_card == "This"
        )

    @staticmethod
    def AfterCardBecomeBoost(ability_type: 'AbilityType',
                             which_card: CardType,
                             operation: OperationType[Message.AfterCardBecomeBoost],
                             *,
                             conditions: ConditionsType[Message.AfterCardBecomeBoost]=[],
                             ) -> 'Ability':

        def check_which_card(effect: 'Effect', message: Message.AfterCardBecomeBoost) -> bool:
            return Condition.CheckWhichCard(which_card, message.trigger, effect)

        return Ability(
            ability_type,
            Message.AfterCardBecomeBoost,
            [
                check_which_card,
                *conditions
            ],
            operation,
            is_local=which_card == "This"
        )

    @staticmethod
    def AfterEnemyGivenBoostCard(ability_type: 'AbilityType',
                                which_enemy: CardType,
                                operation: OperationType[Message.AfterEnemyGivenBoostCard],
                                *,
                                conditions: ConditionsType[Message.AfterEnemyGivenBoostCard]=[],
                                ) -> 'Ability':

        def check_which_enemy(effect: 'Effect', message: Message.AfterEnemyGivenBoostCard) -> bool:
            return Condition.CheckWhichCard(which_enemy, message.trigger, effect)

        return Ability(
            ability_type,
            Message.AfterEnemyGivenBoostCard,
            [
                check_which_enemy,
                *conditions
            ],
            operation,
            is_local=which_enemy == "This"
        )

    @staticmethod
    def WhenEnemyWouldBeGivenBoostCard(ability_type: 'AbilityType',
                                       which_enemy: CardType,
                                       operation: OperationType[Message.WhenEnemyWouldBeGivenBoostCard],
                                       *,
                                       conditions: ConditionsType[Message.WhenEnemyWouldBeGivenBoostCard]=[],
                                       ) -> 'Ability':
        def check_which_enemy(effect: 'Effect', message: Message.WhenEnemyWouldBeGivenBoostCard) -> bool:
            return Condition.CheckWhichCard(which_enemy, message.trigger, effect)

        return Ability(
            ability_type,
            Message.WhenEnemyWouldBeGivenBoostCard,
            [check_which_enemy, *conditions],
            operation,
            is_local=which_enemy == "This",
        )

    ################################################################################
    #
    @staticmethod
    def BoostIfThisActivationDealsDamage(to_who: CardType|Literal["You"],
                                    operation: OperationType[Message.AfterUnitTookDamage]) -> 'Ability':
        from game.card.face.card_type import Identity

        def when_this_boost(effect: 'Effect', message: 'Message.WhenCardBecomeBoost') -> None:
            boost_for_message = message.being_message
            trigger = boost_for_message.trigger
            this = effect.this
            Unused(this)

            def check_who(damage_effect: 'Effect', damage_message: 'Message.AfterUnitTookDamage') -> bool:
                if to_who == "You":
                    return damage_message.trigger.GetControlBy() == message.to_player and \
                        Identity.IsType(damage_message.trigger)
                return Condition.CheckWhichCard(to_who, damage_message.trigger, damage_effect)

            trigger.effect.RegisterTemp(
                Ability(
                    AbilityType.Temp0,
                    Message.AfterUnitTookDamage,
                    [
                        lambda damage_effect, damage_message:
                            damage_message.would_atk_message == boost_for_message.would_message and \
                            damage_message.deal_damage > 0,
                        check_who,
                    ],
                    lambda damage_effect, damage_message:
                        operation(effect, damage_message)
                ),
                unregister_after_exec=True,
                until_turn_end=True,
            )

        return AbilityFactoryBoost.WhenCardBecomeBoost(
            "This",
            when_this_boost,
        )

    @staticmethod
    def WhenBoostShuffleThisIntoEncounterDeckAfterActivationEnd() -> 'Ability':
        from cards.pack import ShuffleThisCardIntoEncounter
        def action(effect: 'Effect', message: 'Message.WhenCardBecomeBoost'):
            this = effect.this
            Unused(this)

            message.AfterThisActivation(
                effect,
                lambda:
                    ShuffleThisCardIntoEncounter(effect, message)
            )

        return AbilityFactoryBoost.WhenCardBecomeBoost(
            "This",
            action
        )

    ################################################################################
    #
    @staticmethod
    # On Encounter Card
    def WhenBoostIconsWouldBeCount(ability_type: 'AbilityType',
                                   operation: OperationType[Message.WhenBoostIconsWouldBeCount],
                                   *,
                                   conditions: ConditionsType[Message.WhenBoostIconsWouldBeCount]=[],
                                   ) -> 'Ability':

        return Ability(
            ability_type,
            Message.WhenBoostIconsWouldBeCount,
            conditions,
            operation,
        )

    @staticmethod
    def WhenBoostCardWouldTurnedFaceUp(ability_type: 'AbilityType',
                                    operation: OperationType[Message.WhenBoostCardWouldTurnedFaceUp],
                                    *,
                                    while_attack: bool|None=None,
                                    while_scheme: bool|None=None, # during_scheme_activation
                                    boost_for_card: CardType=None,
                                    activate_target: CardType|Literal["You"]=None,
                                    # can_be_cancel_boost_icons: bool|None=None,
                                    # can_be_cancel_boost_ability: bool|None=None,
                                    conditions: ConditionsType[Message.WhenBoostCardWouldTurnedFaceUp]=[],
                                    ) -> 'Ability':


        def check_while_attack(effect: 'Effect', message: 'Message.WhenBoostCardWouldTurnedFaceUp') -> bool:
            if while_attack == None:
                return True
            return while_attack == message.being_message.IsAttack()

        def check_while_scheme(effect: 'Effect', message: 'Message.WhenBoostCardWouldTurnedFaceUp') -> bool:
            if while_scheme == None:
                return True
            return while_scheme == message.being_message.IsScheme()

        def check_boost_for_card(effect: 'Effect', message: 'Message.WhenBoostCardWouldTurnedFaceUp') -> bool:
            return Condition.CheckWhichCard(boost_for_card, message.would_message.trigger, effect)

        def check_activate_target(effect: 'Effect', message: 'Message.WhenBoostCardWouldTurnedFaceUp') -> bool:
            if not activate_target:
                return True
            rule = Condition.GetYouRule(activate_target, identity=True)
            if isinstance(message.would_message, AttackerMessageInternal):
                targets = message.would_message.attacked_targets
            else:
                assert False
                # targets = message.would_message.targets
            return Condition.CheckWhichCard(rule, targets, effect)

        return Ability(
            ability_type,
            Message.WhenBoostCardWouldTurnedFaceUp,
            [
                check_while_attack,
                check_while_scheme,
                check_boost_for_card,
                check_activate_target,
                *conditions
            ],
            operation,
        )

    @staticmethod
    def WhenBoostCardTurnedFaceUp(ability_type: 'AbilityType',
                                  canbe_cancel: Literal["BoostIcons", "Ability"]|None,
                                  operation: OperationType[Message.WhenBoostCardTurnedFaceUp],
                                  *,
                                  while_attack: bool|None=None,
                                  while_scheme: bool|None=None, # during_scheme_activation
                                  boost_for_card: CardType=None,
                                  activate_target: CardType=None,
                                  activate_message: 'Message.WhenUnitWouldAttack|Message.WhenUnitWouldScheme|None'=None,
                                  conditions: ConditionsType[Message.WhenBoostCardTurnedFaceUp]=[],
                                  ) -> 'Ability':

        def check_while_attack(effect: 'Effect', message: 'Message.WhenBoostCardTurnedFaceUp') -> bool:
            if while_attack == None:
                return True
            return while_attack == message.being_message.IsAttack()

        def check_while_scheme(effect: 'Effect', message: 'Message.WhenBoostCardTurnedFaceUp') -> bool:
            if while_scheme == None:
                return True
            return while_scheme == message.being_message.IsScheme()

        def check_boost_for_card(effect: 'Effect', message: 'Message.WhenBoostCardTurnedFaceUp') -> bool:
            return Condition.CheckWhichCard(boost_for_card, message.would_message.trigger, effect)

        def check_activate_target(effect: 'Effect', message: 'Message.WhenBoostCardTurnedFaceUp') -> bool:
            if not activate_target:
                return True
            if isinstance(message.would_message, AttackerMessageInternal):
                targets = message.would_message.attacked_targets
            else:
                assert False
                # targets = message.would_message.targets
            return Condition.CheckWhichCard(activate_target, targets, effect)

        def check_activate_message(effect: 'Effect', message: 'Message.WhenBoostCardTurnedFaceUp') -> bool:
            if activate_message == None:
                return True
            return activate_message == message.would_message

        def check_canbe_cancel(effect: 'Effect', message: 'Message.WhenBoostCardTurnedFaceUp') -> bool:
            if canbe_cancel == None:
                return True
            if canbe_cancel == "BoostIcons":
                return not message.cancel_boost_icons and message.boost_icons > 0
            if canbe_cancel == "Ability":
                if not message.trigger.effect.Find(type=AbilityType.Boost):
                    return False
                return not message.cancel_boost_ability

        return Ability(
            ability_type,
            Message.WhenBoostCardTurnedFaceUp,
            [
                check_while_attack,
                check_while_scheme,
                check_boost_for_card,
                check_activate_target,
                check_canbe_cancel,
                check_activate_message,
                *conditions
            ],
            operation,
        )

    @staticmethod
    # On Encounter Card
    def IncreaseBoostIconsOnEncounterCard(*,
                                        conditions: ConditionsType[Message.WhenBoostIconsWouldBeCount]=[]
                                        ) -> 'Ability':


        def operation(effect: 'Effect', message: 'Message.WhenBoostIconsWouldBeCount'):
            message.UpdateBoostIcon(+1, effect)

        return Ability(
            AbilityType.NonKeyword,
            Message.WhenBoostIconsWouldBeCount,
            conditions,
            operation,
        )
