from . import *

class AbilityFactoryDoAttack:

    @staticmethod
    def WhenAttachedPlayerWouldAttack(ability_type: 'AbilityType',
                                    attacker: CardType|Literal["You"],
                                    operation: OperationType[Message.WhenUnitWouldAttack|Message.WhenPlayerWouldPlayCard],
                                    ) -> List['Ability']:
        from game.ability.factory import AbilityFactory
        return [
            AbilityFactory.WhenUnitWouldAttack(
                ability_type,
                attacker,
                operation
            ),
            # Fix: 18012
            AbilityFactory.WhenPlayerWouldPlayCard(
                ability_type,
                "AttachedPlayer",
                None,
                operation,
                conditions=[
                    lambda effect, message:
                        message.play_effect.ability.is_label_attack
                ],
            )
        ]

    # WhenUnitAttack
    @staticmethod
    def WhenUnitWouldAttack(ability_type: 'AbilityType',
                            attacker: CardType|Literal["You"],
                            operation: OperationType[Message.WhenUnitWouldAttack],
                            *,
                            against_player: PlayerType="AnyPlayer",
                            attack_targets: CardType=None,
                            is_basic_attack: bool|None=None,
                            by_effect: 'Effect|None'=None,
                            conditions: ConditionsType[Message.WhenUnitWouldAttack]=[]
                            ) -> 'Ability':

        def check_attacker(effect: 'Effect', message: 'Message.WhenUnitWouldAttack') -> bool:
            rule = Condition.GetYouRule(attacker, identity=True)
            return Condition.CheckWhichCard(rule, message.attacker, effect)

        def check_against_player(effect: 'Effect', message: 'Message.WhenUnitWouldAttack') -> bool:
            return Condition.CheckAgainstPlayer(against_player, message, effect)

        def check_who_be_attacked(effect: 'Effect', message: 'Message.WhenUnitWouldAttack') -> bool:
            return Condition.CheckWhichCard(attack_targets, message.attacked_targets, effect)

        def check_is_basic_attack(effect: 'Effect', message: 'Message.WhenUnitWouldAttack') -> bool:
            if is_basic_attack == None:
                return True
            return is_basic_attack == message.IsBasicAttack()

        def check_by_effect(effect: 'Effect', message: 'Message.WhenUnitWouldAttack') -> bool:
            if by_effect == None:
                return True
            return by_effect == message.by_effect

        return Ability(
            ability_type,
            Message.WhenUnitWouldAttack,
            [
                check_attacker,
                check_against_player,
                check_is_basic_attack,
                check_who_be_attacked,
                check_by_effect,
                *conditions
            ],
            operation,
            is_local=attacker == "This"
        )

    @staticmethod
    def WhenUnitMakeAttack(ability_type: 'AbilityType',
                            attacker: CardType|Literal["You"],
                            operation: OperationType[Message.WhenUnitWouldAttack],
                            *,
                            is_basic_attack: bool|None=None,
                            # attack_targets: CardType=None,
                            # against_player: PlayerType=None,
                            # has_keyword: Literal["Ranged", "Piercing", "Overkill"]=[],
                            conditions: ConditionsType[Message.WhenUnitWouldAttack]=[],
                            ) -> 'Ability':
        return AbilityFactoryDoAttack.WhenUnitWouldAttack(
            ability_type,
            attacker,
            operation,
            # against_player=against_player,
            is_basic_attack=is_basic_attack,
            # has_keyword=has_keyword,
            # attack_targets=attack_targets,
            conditions=conditions
        )

    @staticmethod
    def WhenUnitMakeKeyWordAttack(ability_type: 'AbilityType',
                                attacker: CardType|Literal["You"],
                                operation: OperationType[Message.WhenUnitMakeKeyWordAttack],
                                *,
                                is_basic_attack: bool|None=None,
                                has_keyword: Literal["Ranged", "Piercing", "Overkill", "Any"]="Any",
                                conditions: ConditionsType[Message.WhenUnitMakeKeyWordAttack]=[],
                                ) -> 'Ability':

        def check_attacker(effect: 'Effect', message: 'Message.WhenUnitMakeKeyWordAttack') -> bool:
            rule = Condition.GetYouRule(attacker, identity=True)
            return Condition.CheckWhichCard(rule, message.attacker, effect)

        def check_is_basic_attack(effect: 'Effect', message: 'Message.WhenUnitMakeKeyWordAttack') -> bool:
            if is_basic_attack == None:
                return True
            return is_basic_attack == message.IsBasicAttack()

        def check_has_keyword(effect: 'Effect', message: 'Message.WhenUnitMakeKeyWordAttack') -> bool:
            if has_keyword == "Any":
                return message.would_atk_unit_message.HasKeywords()
            if has_keyword == "Ranged" and not message.would_atk_unit_message.IsRanged():
                return False
            if has_keyword == "Piercing" and not message.would_atk_unit_message.IsPiercing():
                return False
            if has_keyword == "Overkill" and not message.would_atk_unit_message.IsOverKill():
                return False
            return True

        return Ability(
            ability_type,
            Message.WhenUnitMakeKeyWordAttack,
            [
                check_attacker,
                check_is_basic_attack,
                check_has_keyword,
                *conditions
            ],
            operation,
            is_local=attacker == "This"
        )

    @staticmethod
    def WhenUnitInitiatesAttackAgainst(ability_type: 'AbilityType',
                                       attacker: CardType,
                                       against_player: PlayerType,
                                       operation: OperationType[Message.WhenUnitWouldAttack],
                                       conditions: ConditionsType[Message.WhenUnitWouldAttack]=[],
                                       ) -> 'Ability':
        # [x for x in message.targets if x.GetController().IsPlayer()] != [] and \
        # TODO: Test multiple
        return AbilityFactoryDoAttack.WhenUnitWouldAttack(
            ability_type,
            attacker,
            operation,
            against_player=against_player,
            conditions=conditions,
        )

    @staticmethod
    def WhenUnitAttackYou(ability_type: 'AbilityType',
                              attacker: CardType,
                              operation: OperationType[Message.WhenUnitWouldAttack],
                              conditions: ConditionsType[Message.WhenUnitWouldAttack]=[],
                              ) -> 'Ability':
        return AbilityFactoryDoAttack.WhenUnitInitiatesAttackAgainst(
            ability_type,
            attacker,
            "You",
            operation,
            conditions=conditions,
        )

    @staticmethod
    def WhenUnitWouldAttackUnit(ability_type: 'AbilityType',
                                attacker: CardType|Literal["You"],
                                who_be_attacked: CardType,
                                operation: OperationType[Message.WhenUnitWouldAttackUnit],
                                *,
                                is_basic_attack: bool|None=None,
                                conditions: ConditionsType[Message.WhenUnitWouldAttackUnit]=[],
                                ) -> 'Ability':

        def check_attacker(effect: 'Effect', message: 'Message.WhenUnitWouldAttackUnit') -> bool:
            rule = Condition.GetYouRule(attacker, identity=True)
            return Condition.CheckWhichCard(rule, message.attacker, effect)

        def check_who_be_attack(effect: 'Effect', message: 'Message.WhenUnitWouldAttackUnit') -> bool:
            return Condition.CheckWhichCard(who_be_attacked, message.target, effect)

        def check_is_basic_attack(effect: 'Effect', message: 'Message.WhenUnitWouldAttackUnit') -> bool:
            if is_basic_attack == None:
                return True
            # `AfterUnitDefeatedUnit` will also call this function because of `CopyForDelay`
            # return is_basic_attack == message.would_atk_message.property.is_basic_power
            return is_basic_attack == message.IsBasicAttack()

        return Ability(
            ability_type,
            Message.WhenUnitWouldAttackUnit,
            [
                check_attacker,
                check_who_be_attack,
                check_is_basic_attack,
                *conditions
            ],
            operation,
            is_local=attacker == "This" or who_be_attacked == "This"
        )

    # @staticmethod
    # def WhenUnitMakeAttackAgainst(ability_type: 'AbilityType',
    #                             attacker: CardType,
    #                             operation: OperationType[Send.WhenUnitWouldAttackUnit],
    #                             *,
    #                             against_target: 'CardFinder'|Literal["This", "Attached"]|Type['TC']=[],
    #                             is_basic_attack: bool|None=None,
    #                             # against_unique_target: bool|None=None,
    #                             condition: ConditionType[Send.WhenUnitWouldAttackUnit]=[],
    #                             ) -> 'Ability':
    #     return AbilityFactoryAttack.WhenUnitWouldAttackUnit(
    #         ability_type,
    #         attacker,
    #         against_target,
    #         operation,
    #         is_basic_attack=is_basic_attack,
    #         # against_unique_target=against_unique_target,
    #         condition=condition
    #     )

    @staticmethod
    def WhenUnitDefendAgainstAttack(ability_type: 'AbilityType',
                                    who_defense: CardType|Literal["You"],
                                    operation: OperationType[Message.WhenUnitWouldDefend],
                                    *,
                                    against_who: CardType=None,
                                    is_basic_defense: bool|None=None,
                                    conditions: ConditionsType[Message.WhenUnitWouldDefend]=[],) -> 'Ability':
        from game.card.face.card_type import Hero

        def check_who_defense(effect: 'Effect', message: 'Message.WhenUnitWouldDefend') -> bool:
            if who_defense == "You":
                return Condition.ThisIsYou(effect, message.trigger) and \
                    effect.GetInitiator().GetIdentity() == message.trigger
            if who_defense == "YourHero":
                return Condition.ThisIsYou(effect, message.trigger) and \
                    Hero.IsType(message.trigger) and \
                    effect.GetInitiator().GetIdentity() == message.trigger
            return Condition.CheckWhichCard(who_defense, message.trigger, effect)

        def check_against_who(effect: 'Effect', message: 'Message.WhenUnitWouldDefend') -> bool:
            return Condition.CheckWhichCard(against_who, message.attacker, effect)

        def check_is_basic_defense(effect: 'Effect', message: 'Message.WhenUnitWouldDefend') -> bool:
            if is_basic_defense == None:
                return True
            return is_basic_defense == message.IsBasicDefense()

        return Ability(
            ability_type,
            Message.WhenUnitWouldDefend,
            [
                check_who_defense,
                check_against_who,
                check_is_basic_defense,
                *conditions
            ],
            operation,
            is_local=who_defense == "This" or against_who == "This"
        )

    # We keep this for "01082" description
    @staticmethod
    def AfterUnitDefendEnd(ability_type: 'AbilityType',
                        who_defense: CardType|Literal["You"],
                        operation: OperationType[Message.AfterUnitDefendEnd],
                        *,
                        conditions: ConditionsType[Message.AfterUnitDefendEnd]=[],
                        ) -> 'Ability':
        return AbilityFactoryDoAttack.AfterUnitDefendAgainstAttack(
            ability_type,
            who_defense,
            operation,
            conditions=conditions,
        )

    @staticmethod
    def AfterUnitDefendAgainstAttack(ability_type: 'AbilityType',
                                     who_defense: CardType|Literal["You"],
                                     operation: OperationType[Message.AfterUnitDefendEnd],
                                     *,
                                     attacker: CardType=None,
                                     against_which_attack: 'Message.WhenUnitWouldAttack|None'=None,
                                     take_no_damage: bool|None=None,
                                     conditions: ConditionsType[Message.AfterUnitDefendEnd]=[],
                                     ) -> 'Ability':

        def check_who_defense(effect: 'Effect', message: 'Message.AfterUnitDefendEnd') -> bool:
            # if message.defender == None:
            #     return False
            rule = Condition.GetYouRule(who_defense, identity=True)
            return Condition.CheckWhichCard(rule, message.defender, effect)

        def check_attacker(effect: 'Effect', message: 'Message.AfterUnitDefendEnd') -> bool:
            return Condition.CheckWhichCard(attacker, message.attacker, effect)

        def check_against_attack(effect: 'Effect', message: 'Message.AfterUnitDefendEnd') -> bool:
            if against_which_attack == None:
                return True
            return against_which_attack == message.would_atk_message

        def check_take_no_damage(effect: 'Effect', message: 'Message.AfterUnitDefendEnd') -> bool:
            if take_no_damage == None:
                return True
            return message.taken_damage == 0

        return Ability(
            ability_type,
            Message.AfterUnitDefendEnd,
            [
                # message.defender != None and \
                check_who_defense,
                check_attacker,
                check_against_attack,
                check_take_no_damage,
                *conditions
            ],
            operation,
            is_local=who_defense == "This" or attacker == "This"
        )

    @staticmethod
    def WhenUnitAttackDealExcessDamage(ability_type: 'AbilityType',
                                       who_deal: CardType|Literal["You"],
                                       operation: OperationType[Message.WhenCalcDealExcessDamage],
                                       *,
                                       conditions: ConditionsType[Message.WhenCalcDealExcessDamage]=[],
                                       ) -> 'Ability':

        def check_who_deal(effect: 'Effect', message: 'Message.WhenCalcDealExcessDamage') -> bool:
            rule = Condition.GetYouRule(who_deal, identity=True)
            return Condition.CheckWhichCard(rule, message.attacker, effect)

        return Ability(
            ability_type,
            Message.WhenCalcDealExcessDamage,
            [
                check_who_deal,
                *conditions
            ],
            operation,
            is_local=who_deal == "This"
        )

    @staticmethod
    def AfterUnitAttackUnitInternal(ability_type: 'AbilityType',
                                    attacker: CardType|Literal["You"],
                                    who_be_attacked: CardType|Literal["You"],
                                    operation: OperationType[Message.AfterUnitAttackUnit],
                                    *,
                                    atk_message: 'Message.WhenUnitWouldAttackUnit|None'=None,
                                    use_atk: bool|None=None,
                                    dealt_damage: bool|None=None,
                                    dealt_more_than_damage: int|None=None,
                                    target_took_damage: bool|None=None,
                                    is_undefended_attack: bool|None=None,
                                    who_is_target: 'CardFace|None'=None,
                                    conditions: ConditionsType[Message.AfterUnitAttackUnit]=[],
                                    ) -> 'Ability':
        from game.card.face.card_type import Identity
        from game.card.face.base import ClassCard

        def check_attacker(effect: 'Effect', message: 'Message.AfterUnitAttackUnit') -> bool:
            rule = Condition.GetYouRule(attacker, identity=True)
            return Condition.CheckWhichCard(rule, message.trigger, effect)

            # TODO: Check this
            """
            if is not PlayerCard, get player use:
                player = message.target.GetPlayer()
            """

            """
            Exception: For abilities that trigger “after [enemy]
            attacks you,” “you” refers to the attacked player, even
            if that player defended with an ally.
            """
            return message.attacker != None and attacker.IsType(message.attacker)

        def check_atk_message(effect: 'Effect', message: 'Message.AfterUnitAttackUnit') -> bool:
            if atk_message == None:
                return True
            return atk_message == message.would_atk_unit_message

        def check_who_be_attacked(effect: 'Effect', message: 'Message.AfterUnitAttackUnit') -> bool:
            from game.card.face.base import EncounterCard
            # For abilities that trigger “after [enemy] attacks you,” “you” refers to the attacked player, even if that player defended with an ally.
            # Attacks are always made against a player. If you choose to defend with an ally, the attack was still against you. It is just defended by your ally. I know that’s not clear with the current rules reference. We’re going to be updating that as soon as our schedule allows.
            # “after [enemy] attacks you” refers to the player whose character defended the attack
            if who_be_attacked == "You":
                if dealt_damage:
                    if ClassCard.IsType(effect.this):
                        return message.to_player != None and \
                            effect.initiator == message.to_player
                    else:
                        return message.to_player != None and \
                            message.attacked.GetControlBy() == message.to_player and \
                            Identity.IsType(message.attacked)
                else:
                    if message.attacked_you == None:
                        return False
                    if EncounterCard.IsType(effect.this):
                        return True
                    return Condition.ThisIsYou(effect, message.attacked_you)
                    # if effect.IsPlayerInitiator():
                    #     return effect.initiator == message.to_player
                    # else:
                    #     return message.to_player != None
                    #     # message.target.GetController() == message.to_player
            return Condition.CheckWhichCard(who_be_attacked, message.attacked, effect)

        def check_use_atk(effect: 'Effect', message: 'Message.AfterUnitAttackUnit') -> bool:
            if use_atk == None:
                return True
            return use_atk == message.would_atk_message.IsBasicAttack()

        def check_dealt_damage(effect: 'Effect', message: 'Message.AfterUnitAttackUnit') -> bool:
            if dealt_damage == None:
                return True
            return message.dealt_damage > 0

        def check_dealt_more_than_damage(effect: 'Effect', message: 'Message.AfterUnitAttackUnit') -> bool:
            if dealt_more_than_damage == None:
                return True
            return message.dealt_damage >= dealt_more_than_damage

        def check_target_took_damage(effect: 'Effect', message: 'Message.AfterUnitAttackUnit') -> bool:
            if target_took_damage == None:
                return True
            rule = Condition.GetYouRule(who_be_attacked, identity=True)
            return Condition.CheckWhichCard(rule, message.attacked, effect) and \
                message.taken_damage > 0

        def check_is_undefended_attack(effect: 'Effect', message: 'Message.AfterUnitAttackUnit') -> bool:
            if is_undefended_attack == None:
                return True
            if is_undefended_attack:
                return message.defender == None
            else:
                return message.defender != None

        def check_who_is_target(effect: 'Effect', message: 'Message.AfterUnitAttackUnit') -> bool:
            if who_is_target == None:
                return True
            return who_is_target.card.face == message.attacked

        return Ability(
            ability_type,
            Message.AfterUnitAttackUnit,
            [
                check_dealt_damage,
                check_attacker,
                check_atk_message,
                check_who_be_attacked,
                check_use_atk,
                check_dealt_more_than_damage,
                check_target_took_damage,
                check_is_undefended_attack,
                check_who_is_target,
                *conditions
            ],
            operation,
            is_local=attacker == "This" or who_be_attacked == "This"
        )

    @staticmethod
    def AfterUnitAttackAndDamageUnit(ability_type: 'AbilityType',
                                    attacker: CardType,
                                    who_be_attacked: CardType|Literal["You", "YouControlCharacter"],
                                    operation: OperationType[Message.AfterUnitAttackUnit],
                                    *,
                                    target_in_play: bool|None=None,
                                    use_atk: bool|None=None,
                                    dealt_more_than_damage: int|None=None,
                                    conditions: ConditionsType[Message.AfterUnitAttackUnit]=[],
                                    # control_by_player: bool|None=None, # attack you control character
                                    ) -> 'Ability':
        # from game.player import Player

        # control_by_player = None
        # if who_be_attacked == "YouControlCharacter":
        #     who_be_attacked = None
        #     control_by_player = True

        def check_target_in_play(effect: 'Effect', message: 'Message.AfterUnitAttackUnit') -> bool:
            if target_in_play == None:
                return True
            return message.attacked.IsInPlay()

        # def check_control_by_player(effect: 'Effect', message: 'Message.AfterUnitAttackUnit') -> bool:
        #     if control_by_player == None:
        #         return True
        #     return Player.IsType(message.attacked.GetControlBy())

        return AbilityFactoryDoAttack.AfterUnitAttackUnit(
            ability_type,
            attacker,
            who_be_attacked,
            operation,
            use_atk=use_atk,
            target_took_damage=True,
            dealt_more_than_damage=dealt_more_than_damage,
            conditions=[
                check_target_in_play,
                # check_control_by_player,
                *conditions
            ],
        )

    @staticmethod
    def AfterUnitDealsDamageWithSingleAttack(ability_type: 'AbilityType',
                                            attacker: CardType,
                                            who_be_damaged: CardType,
                                            operation: OperationType[Message.AfterFaceDealDamage|Message.AfterUnitAttackUnit],
                                            *,
                                            dealt_more_than_damage: int|None=None,
                                            # conditions: ConditionsType[Message.AfterFaceDealDamage|Message.AfterUnitAttackUnit]=[],
                                            ) -> List['Ability']:
        from game.ability.factory import AbilityFactory

        return [
            AbilityFactory.AfterFaceDealDamage(
                ability_type,
                attacker,
                who_be_damaged,
                operation,
                is_from_attack=True,
                dealt_more_than_damage=dealt_more_than_damage,
                # conditions=conditions,
            ),
            AbilityFactory.AfterUnitAttackUnit(
                AbilityType.ForcedResponse,
                attacker,
                who_be_damaged,
                operation,
                dealt_more_than_damage=dealt_more_than_damage,
                # conditions=conditions,
            ),
        ]

    @staticmethod
    def AfterUnitAttackUnit(ability_type: 'AbilityType',
                            attacker: CardType|Literal["You"],
                            who_be_attacked: CardType|Literal["You", "YouControlCharacter"],
                            operation: OperationType[Message.AfterUnitAttackUnit],
                            *,
                            use_atk: bool|None=None,
                            dealt_damage: bool|None=None,
                            target_took_damage: bool|None=None, # damages target
                            dealt_more_than_damage: int|None=None,
                            is_undefended_attack: bool|None=None,
                            conditions: ConditionsType[Message.AfterUnitAttackUnit]=[],
                            ) -> 'Ability':
        from game.card.card_finder import CardFinder
        from game.player import Player

        if not isinstance(who_be_attacked, CardFinder) and \
            who_be_attacked != "YouControlCharacter":
            return AbilityFactoryDoAttack.AfterUnitAttackUnitInternal(
                ability_type,
                attacker,
                who_be_attacked,
                operation,
                use_atk=use_atk,
                dealt_damage=dealt_damage,
                target_took_damage=target_took_damage,
                dealt_more_than_damage=dealt_more_than_damage,
                is_undefended_attack=is_undefended_attack,
                conditions=conditions
            )
        else:
            def action(effect: 'Effect', message: 'Message.WhenUnitWouldAttackUnit') -> None:
                this = effect.this
                target = message.target

                if who_be_attacked == "YouControlCharacter":
                    finder = None
                    Player.IsType(message.target.GetControlBy())
                else:
                    assert who_be_attacked == None or isinstance(who_be_attacked, CardFinder)
                    finder = who_be_attacked

                if not finder or finder.Check(target):
                    ability = AbilityFactoryDoAttack.AfterUnitAttackUnitInternal(
                        ability_type,
                        attacker,
                        None,
                        operation,
                        use_atk=use_atk,
                        dealt_damage=dealt_damage,
                        target_took_damage=target_took_damage,
                        dealt_more_than_damage=dealt_more_than_damage,
                        is_undefended_attack=is_undefended_attack,
                        who_is_target=target,
                        conditions=conditions,
                    )
                    ability.CopyFromDelayEffect(effect)
                    this.effect.RegisterTemp(
                        ability,
                        unregister_after_exec=True,
                        until_event_end=message
                    )

            return AbilityFactoryDoAttack.WhenUnitWouldAttackUnit(
                AbilityType.DelayAbility,
                attacker,
                None,
                action
            )

    @staticmethod
    def AfterUnitAttackEnd(ability_type: 'AbilityType',
                           attacker: CardType|Literal["You"],
                           operation: OperationType[Message.AfterUnitAttackEnd],
                           *,
                           is_basic_attack: bool|None=None,
                           damaged_who: CardType=None,
                           against_who: CardType|Literal["You"]=None,
                           conditions: ConditionsType[Message.AfterUnitAttackEnd]=[],
                           would_atk_message: 'Message.WhenUnitWouldAttack|None'=None,
                           ) -> 'Ability':

        def check_is_basic_attack(effect: 'Effect', message: 'Message.AfterUnitAttackEnd') -> bool:
            if is_basic_attack == None:
                return True
            return is_basic_attack == message.IsBasicAttack()

        def check_against_who(effect: 'Effect', message: 'Message.AfterUnitAttackEnd') -> bool:
            if against_who == None:
                return True
            if against_who == "You":
                against_player = message.GetAgainstPlayer()
                if against_who:
                    return against_player != None
                else:
                    return against_player == None
            return Condition.CheckWhichCard(against_who, message.attacked_targets, effect)

        def check_damage_who(effect: 'Effect', message: 'Message.AfterUnitAttackEnd') -> bool:
            if damaged_who == None:
                return True
            return Condition.CheckWhichCard(damaged_who, message.damaged_targets, effect)

        def check_attacker(effect: 'Effect', message: 'Message.AfterUnitAttackEnd') -> bool:
            rule = Condition.GetYouRule(attacker, identity=True)
            return Condition.CheckWhichCard(rule, message.attacker, effect)

        def check_would_atk_message(effect: 'Effect', message: 'Message.AfterUnitAttackEnd') -> bool:
            if would_atk_message == None:
                return True
            return would_atk_message in message.would_atk_messages

        return Ability(
            ability_type,
            Message.AfterUnitAttackEnd,
            [
                check_attacker,
                check_is_basic_attack,
                check_against_who,
                check_damage_who,
                check_would_atk_message,
                *conditions
            ],
            operation,
            is_local=attacker == "This" or damaged_who == "This" or against_who == "This"
        )

    @staticmethod
    def AfterUnitAttackYou(ability_type: 'AbilityType',
                           attacker: CardType,
                           operation: OperationType[Message.AfterUnitAttackEnd],
                           *,
                           conditions: ConditionsType[Message.AfterUnitAttackEnd]=[],
                           ) -> 'Ability':
        return AbilityFactoryDoAttack.AfterUnitAttackEnd(
            ability_type,
            attacker,
            operation,
            conditions=conditions,
            against_who="You"
        )

    @staticmethod
    def AfterUnitMakeBasicAttack(ability_type: 'AbilityType',
                                attacker: CardType|Literal["You"],
                                operation: OperationType[Message.AfterUnitAttackEnd],
                                *,
                                damage_who: CardType=None,
                                against_who: CardType=None,
                                ) -> 'Ability':

        return AbilityFactoryDoAttack.AfterUnitAttackEnd(
            ability_type,
            attacker,
            operation,
            against_who=against_who,
            damaged_who=damage_who,
            is_basic_attack=True,
        )

    # @staticmethod
    # def AfterUnitMakeAttack(ability_type: 'AbilityType',
    #                         attacker: CardType|Literal["You"],
    #                         operation: OperationType[Message.AfterUnitAttackEnd],
    #                         *,
    #                         is_basic_attack: bool|None=None,
    #                         damage_who: CardType=None,
    #                         against_who: CardType=None,
    #                         ) -> 'Ability':

    #     return AbilityFactoryDoAttack.AfterUnitAttackEnd(
    #         ability_type,
    #         attacker,
    #         operation,
    #         against_who=against_who,
    #         damage_who=damage_who,
    #         is_basic_attack=is_basic_attack,
    #     )

    @staticmethod
    def UnitGetATKWhileAttacking(ability_type: 'AbilityType',
                                which_card: CardType|Literal["This", "AttachedCharacter", "EnemyLeader"],
                                target: CardType,
                                calc_fn: Callable[['Effect', 'Message.WhenCalculateAttackDamage'], int]|int,
                                *,
                                is_undefended_attack: bool|None=None,
                                ) -> List['Ability']:
        from game.ability.factory import AbilityFactory

        def check_player(effect: 'Effect', message: 'Message.WhenEffectWouldResolve') -> bool:
            return Condition.CheckWhichCard(which_card, message.GetToPlayer().GetIdentity(), effect)

        def gain_attack_damage(effect: 'Effect', message: 'Message.WhenEffectWouldResolve') -> None:
            assert isinstance(calc_fn, int)
            value = calc_fn
            # if isinstance(calc_fn, int):
            #     value = calc_fn
            # else:
            #     value = calc_fn(effect, message)

            message.effect.initiator.GetRoleCharacter().TemporaryGain(effect, message, attack=value)

        return [
            AbilityFactory.WhenCardWouldResolveAbility(
                ability_type,
                None,
                None,
                gain_attack_damage,
                label='attack',
                trigger_player="You",
                conditions=[
                    check_player,
                ]
            ),
            AbilityFactoryDoAttack.UnitGetATKWhileAttackingInternal(
                ability_type,
                which_card,
                target,
                calc_fn,
                is_undefended_attack=is_undefended_attack
            )
        ]

    # WhileThisIsAttacking
    # Only basic attack
    # BUG: "25006" "25018"
    @staticmethod
    def UnitGetATKWhileAttackingInternal(ability_type: 'AbilityType',
                                        which_card: CardType|Literal["This", "AttachedCharacter", "EnemyLeader"],
                                        target: CardType,
                                        calc_fn: Callable[['Effect', 'Message.WhenCalculateAttackDamage'], int]|int,
                                        *,
                                        is_undefended_attack: bool|None=None,
                                        ) -> 'Ability':
        def gain_attack_damage(effect: 'Effect', message: 'Message.WhenCalculateAttackDamage') -> None:
            if isinstance(calc_fn, int):
                value = calc_fn
            else:
                value = calc_fn(effect, message)

            message.IncreaseDamage(value, effect)

        def check_this(effect: 'Effect', message: 'Message.WhenCalculateAttackDamage') -> bool:
            return Condition.CheckWhichCard(which_card, message.trigger, effect)
            # this = effect.this
            # if which_card == "This":
            #     return this == message.trigger
            # if which_card == "Attached":
            #     return Condition.ThisAttachedTo(effect, message.trigger)
            # assert False

        def check_target(effect: 'Effect', message: 'Message.WhenCalculateAttackDamage') -> bool:
            if target == None:
                return True
            return Condition.CheckWhichCard(target, message.target, effect)

        def check_is_basic_attack(effect: 'Effect', message: 'Message.WhenCalculateAttackDamage') -> bool:
            return message.would_atk_message.IsBasicAttack()

        def check_is_undefended_attack(effect: 'Effect', message: 'Message.WhenCalculateAttackDamage') -> bool:
            if is_undefended_attack == None:
                return True
            return is_undefended_attack == (message.would_atk_message.GetDefender() == None)

        return Ability(
            ability_type,
            Message.WhenCalculateAttackDamage,
            [
                check_is_basic_attack,
                check_target,
                check_this,
                check_is_undefended_attack,
            ],
            gain_attack_damage
        )

    @staticmethod
    def UnitAttackGainKeyword(attacker: CardType|Literal["You"],
                              target: CardType=None,
                              *,
                              is_basic_attack: bool|None=None,
                              conditions: ConditionsType[Message.CheckIfAttackMessageHasKeyword]=[],
                              overkill: bool=False,
                              ranged: bool=False,
                              piercing: bool=False,
                              indirect_damage: bool=False,
                              ignore_retaliate: bool=False,
                              lost_piercing: bool=False) -> 'Ability':

        def gain(effect: 'Effect', message: 'Message.CheckIfAttackMessageHasKeyword') -> None:
            if overkill:
                message.GainOverKill(effect)
            if ranged:
                message.GainRanged(effect)
            if piercing:
                message.GainPiercing(effect)
            if indirect_damage:
                message.SetDealIndirectDamage(effect)
            if ignore_retaliate:
                message.SetIgnoreRetaliate(effect)
            if lost_piercing:
                message.SetLostPiercing(effect)

        def check_attacker(effect: 'Effect', message: 'Message.CheckIfAttackMessageHasKeyword') -> bool:
            rule = Condition.GetYouRule(attacker, identity=True)
            return Condition.CheckWhichCard(rule, message.attacker, effect)

        def check_target(effect: 'Effect', message: 'Message.CheckIfAttackMessageHasKeyword') -> bool:
            return Condition.CheckWhichCard(target, message.targets, effect)

        def check_is_basic_attack(effect: 'Effect', message: 'Message.CheckIfAttackMessageHasKeyword') -> bool:
            if is_basic_attack == None:
                return True
            return is_basic_attack == message.IsBasicAttack()

        return Ability(
            AbilityType.NonKeyword,
            Message.CheckIfAttackMessageHasKeyword,
            [
                check_attacker,
                check_target,
                check_is_basic_attack,
                *conditions
            ],
            gain,
            is_local=attacker == "This"
        )

    @staticmethod
    def WhenUnitWouldBeAttacked(ability_type: 'AbilityType',
                                who_be_attacked: CardType,
                                operation: OperationType[Message.WhenUnitWouldAttack],
                                *,
                                conditions: ConditionsType[Message.WhenUnitWouldAttack]=[],
                                ) -> 'Ability':
        from game.card.face.card_type import Upgrade
        from game.card.face.card_type import Attachment


        def check_who_be_attacked(effect: 'Effect', message: 'Message.WhenUnitWouldAttack') -> bool:
            # TODO: Check
            if who_be_attacked == "Attached":
                # Condition.ThisAttachedToTrigger,
                return isinstance(effect.this, Attachment|Upgrade) and \
                    effect.this.bind_face != None and \
                    message.HasTarget(effect.this.bind_face)
            return Condition.CheckWhichCard(who_be_attacked, message.attacked_targets, effect)

        return Ability(
            ability_type,
            Message.WhenUnitWouldAttack,
            [
                check_who_be_attacked,
                *conditions
            ],
            operation,
            is_local=who_be_attacked == "This"
        )

    @staticmethod
    def AfterUnitBeAttacked(ability_type: 'AbilityType',
                            who_be_attacked: CardType,
                            operation: OperationType[Message.AfterUnitAttackUnit],
                            *,
                            attacker: CardType=None,
                            conditions: ConditionsType[Message.AfterUnitAttackUnit]=[],
                            ) -> 'Ability':

        def check_who_be_attacked(effect: 'Effect', message: 'Message.AfterUnitAttackUnit') -> bool:
            return Condition.CheckWhichCard(who_be_attacked, message.attacked, effect)

        def check_attacker(effect: 'Effect', message: 'Message.AfterUnitAttackUnit') -> bool:
            return Condition.CheckWhichCard(attacker, message.attacker, effect)

        return Ability(
            ability_type,
            Message.AfterUnitAttackUnit,
            [
                check_who_be_attacked,
                check_attacker,
                *conditions
            ],
            operation,
            is_local=attacker == "This" or who_be_attacked == "This"
        )

    ################################################################################
    #
    @staticmethod
    def WhenUnitBeingAttack(ability_type: 'AbilityType',
                            who_be_attacked: CardType|Literal["You"],
                            attacker: CardType,
                            operation: OperationType[Message.WhenUnitBeingAttack],
                            *,
                            has_defender: bool|None=None,
                            is_basic_attack: bool|None=None,
                            would_atk_message: 'Message.WhenUnitWouldAttack|None'=None,
                            conditions: ConditionsType[Message.WhenUnitBeingAttack]=[],
                            ) -> 'Ability':

        def check_who_be_attacked(effect: 'Effect', message: Message.WhenUnitBeingAttack) -> bool:
            rule = Condition.GetYouRule(who_be_attacked, identity=True)
            return Condition.CheckWhichCard(rule, message.trigger, effect)

        def check_attacker(effect: 'Effect', message: Message.WhenUnitBeingAttack) -> bool:
            return Condition.CheckWhichCard(attacker, message.attacker, effect)

        def check_has_defender(effect: 'Effect', message: Message.WhenUnitBeingAttack) -> bool:
            if has_defender == None:
                return True
            return has_defender == (message.defender != None)

        def check_is_basic_attack(effect: 'Effect', message: 'Message.WhenUnitBeingAttack') -> bool:
            if is_basic_attack == None:
                return True
            return is_basic_attack == message.IsBasicAttack()

        def check_atk_message(effect: 'Effect', message: 'Message.WhenUnitBeingAttack') -> bool:
            if would_atk_message == None:
                return True
            return would_atk_message == message.would_atk_message

        return Ability(
            ability_type,
            Message.WhenUnitBeingAttack,
            [
                check_who_be_attacked,
                check_attacker,
                check_has_defender,
                check_is_basic_attack,
                check_atk_message,
                *conditions
            ],
                # effect.GetInitiator().GetIdentity().HasTrait('X-MEN') and \
            operation,
            is_local=who_be_attacked == "This" or attacker == "This"
        )

    @staticmethod
    def UnitCannotBeAttacked(which_unit: CardType,
                            *,
                            conditions: ConditionsType[Message.CheckIfUnitCanBeAttackBy]=[],
                            ) -> 'Ability':

        def check_which_unit(effect: 'Effect', message: 'Message.CheckIfUnitCanBeAttackBy') -> bool:
            return Condition.CheckWhichCard(which_unit, message.being_attack, effect)

        return Ability(
            AbilityType.NonKeyword,
            Message.CheckIfUnitCanBeAttackBy,
            [
                check_which_unit,
                *conditions
            ],
            lambda effect, message:
                message.SetCannotBeAttack(effect),
            is_local=which_unit == "This"
        )

    @staticmethod
    def UnitCannotAttackTarget(attacker: CardType,
                               *,
                               cannot_attack: CardType|Literal[True]=None,
                               can_only_attack: CardType=None,
                               cannot_trigger_attack_ability: bool|None=None,
                               conditions: ConditionsType[Message.CheckIfUnitCanBeAttackBy]=[],
                               ) -> List['Ability']:
        from game.ability.factory import AbilityFactory

        def check_attacker(effect: 'Effect', message: 'Message.CheckIfUnitCanBeAttackBy') -> bool:
            return Condition.CheckWhichCard(attacker, message.attacker, effect)

        def check_cannot_attack(effect: 'Effect', message: 'Message.CheckIfUnitCanBeAttackBy') -> bool:
            if cannot_attack == True:
                return True
            return Condition.CheckWhichCard(cannot_attack, message.being_attack, effect)

        def check_can_only_attack(effect: 'Effect', message: 'Message.CheckIfUnitCanBeAttackBy') -> bool:
            if can_only_attack == None:
                return True
            return not Condition.CheckWhichCard(can_only_attack, message.being_attack, effect)

        if cannot_attack == True:
            abilities = [
                Ability(
                    AbilityType.NonKeyword,
                    Message.CheckIfUnitCanAttack,
                    [
                        lambda effect, message:
                            Condition.CheckWhichCard(attacker, message.check_unit, effect)
                    ],
                    lambda effect, message:
                        message.SetCannotAttack(effect),
                    is_local=attacker == "This"
                )
            ]
        else:
            abilities = [
                Ability(
                    AbilityType.NonKeyword,
                    Message.CheckIfUnitCanBeAttackBy,
                    [
                        check_attacker,
                        check_cannot_attack,
                        check_can_only_attack,
                        *conditions,
                    ],
                    lambda effect, message:
                        message.SetCannotBeAttack(effect),
                    is_local=attacker == "This" or cannot_attack == "This"
                    #  or can_only_attack == "This"
                )
            ]

        if attacker == "AttachedIdentity" and cannot_trigger_attack_ability != False:
            abilities.append(
                AbilityFactory.PlayersCannotTriggerAbility(
                    "AttachedPlayer",
                    None,
                    label='attack',
                ),
            )

        return abilities


    @staticmethod
    def UnitCannotMakeBasicDefense(which_unit: CardType,
                                    who_attacker: CardType,
                                    *,
                                    conditions: ConditionsType[Message.CheckIfUnitCanDefendAgainstAttack]=[],
                                    ) -> List['Ability']:
        return AbilityFactoryDoAttack.UnitCannotDefend(
            which_unit,
            who_attacker,
            cannot_trigger_defense_ability=False,
            conditions=conditions
        )

    @staticmethod
    def UnitCannotDefend(which_unit: CardType,
                          who_attacker: CardType,
                          *,
                          cannot_trigger_defense_ability: bool,
                          conditions: ConditionsType[Message.CheckIfUnitCanDefendAgainstAttack]=[],
                          ) -> List['Ability']:
        from game.ability.factory import AbilityFactory

        def check_which_unit(effect: 'Effect', message: 'Message.CheckIfUnitCanDefendAgainstAttack') -> bool:
            return Condition.CheckWhichCard(which_unit, message.check_unit, effect)

        def check_attacker(effect: 'Effect', message: 'Message.CheckIfUnitCanDefendAgainstAttack') -> bool:
            return Condition.CheckWhichCard(who_attacker, message.attacker, effect)

        abilities = [
            Ability(
                AbilityType.NonKeyword,
                Message.CheckIfUnitCanDefendAgainstAttack,
                [
                    check_which_unit,
                    check_attacker,
                    *conditions,
                ],
                lambda effect, message:
                    message.SetCannotDefend(effect),
                is_local=which_unit == "This" or who_attacker == "This"
            )
        ]

        if cannot_trigger_defense_ability != False:
            if cannot_trigger_defense_ability == True and which_unit == "Attached":
                check_player = "AttachedPlayer"
            elif which_unit:
                assert isinstance(which_unit, CardFinder)
                check_player = PlayerFinder(which_unit)
            else:
                check_player = "AnyPlayer"
            def check_attacker2(effect: 'Effect', message: 'Message.CheckEffectCondition') -> bool:
                return Condition.CheckWhichCard(who_attacker, message.GetAttacker(), effect)
            abilities.append(
                AbilityFactory.PlayersCannotTriggerAbility(
                    check_player,
                    None,
                    label='defense',
                    conditions=[
                        check_attacker2
                    ],
                )
            )

        return abilities

    @staticmethod
    def AfterUnitAttackOrThwart(ability_type: 'AbilityType',
                            attacker: CardType,
                            operation: OperationType[Message.AfterUnitAttackEnd|Message.AfterUnitThwartEnd],
                            *,
                            is_basic_power: bool|None=None,
                            conditions: ConditionsType[Message.AfterUnitAttackEnd|Message.AfterUnitThwartEnd]=[],
                            ) -> 'Ability':

        def check_is_basic_power(effect: 'Effect', message: 'Message.AfterUnitAttackEnd|Message.AfterUnitThwartEnd') -> bool:
            if is_basic_power == None:
                return True
            if isinstance(message, Message.AfterUnitAttackEnd):
                return is_basic_power == message.IsBasicAttack()
            else:
                return is_basic_power == message.IsBasicThwart()

        def check_trigger(effect: 'Effect', message: 'Message.AfterUnitAttackEnd|Message.AfterUnitThwartEnd') -> bool:
            return Condition.CheckWhichCard(attacker, message.trigger, effect)

        return Ability(
            ability_type,
            Message.AfterUnitAttackEnd|Message.AfterUnitThwartEnd,
            [
                check_trigger,
                check_is_basic_power,
                *conditions
            ],
            operation,
            is_local=attacker == "This"
        )


    @staticmethod
    def AfterUnitAttackOrDefend(ability_type: 'AbilityType',
                            which_unit: CardType|Literal["You"],
                            operation: OperationType[Message.AfterUnitAttackEnd|Message.AfterUnitDefendEnd],
                            *,
                            is_basic_power: bool|None=None,
                            conditions: ConditionsType[Message.AfterUnitAttackEnd|Message.AfterUnitDefendEnd]=[],
                            ) -> 'Ability':

        def check_is_basic_power(effect: 'Effect', message: 'Message.AfterUnitAttackEnd|Message.AfterUnitDefendEnd') -> bool:
            if is_basic_power == None:
                return True
            if isinstance(message, Message.AfterUnitAttackEnd):
                return is_basic_power == message.IsBasicAttack()
            else:
                for would_def_message in message.would_def_messages:
                    if is_basic_power == would_def_message.IsBasicDefense():
                        return True
                return False

        def check_trigger(effect: 'Effect', message: 'Message.AfterUnitAttackEnd|Message.AfterUnitDefendEnd') -> bool:
            rule = Condition.GetYouRule(which_unit, identity=True)
            return Condition.CheckWhichCard(rule, message.trigger, effect)

        return Ability(
            ability_type,
            Message.AfterUnitAttackEnd|Message.AfterUnitDefendEnd,
            [
                check_trigger,
                check_is_basic_power,
                *conditions
            ],
            operation,
            is_local=which_unit == "This"
        )

    @staticmethod
    def WhenUnitWouldAttackOrThwart(ability_type: 'AbilityType',
                                    attacker: CardType,
                                    operation: OperationType[Message.WhenUnitWouldAttack|Message.WhenUnitWouldThwart],
                                    *,
                                    is_basic_power: bool|None=None,
                                    conditions: ConditionsType[Message.WhenUnitWouldAttack|Message.WhenUnitWouldThwart]=[],
                                    ) -> 'Ability':

        def check_is_basic_power(effect: 'Effect', message: 'Message.WhenUnitWouldAttack|Message.WhenUnitWouldThwart') -> bool:
            if is_basic_power == None:
                return True
            if isinstance(message, Message.WhenUnitWouldAttack):
                return is_basic_power == message.IsBasicAttack()
            else:
                return is_basic_power == message.IsBasicThwart()

        def check_trigger(effect: 'Effect', message: 'Message.WhenUnitWouldAttack|Message.WhenUnitWouldThwart') -> bool:
            return Condition.CheckWhichCard(attacker, message.trigger, effect)

        return Ability(
            ability_type,
            Message.WhenUnitWouldAttack|Message.WhenUnitWouldThwart,
            [
                check_trigger,
                check_is_basic_power,
                *conditions
            ],
            operation,
            is_local=attacker == "This"
        )

    @staticmethod
    def AfterUnitBecomeDefender(ability_type: 'AbilityType',
                                operation: OperationType[Message.AfterUnitBecomeDefender],
                                *,
                                # attacker: CardType,
                                by_effect_face: CardType=None,
                                # on_event: Type[Message2]=[],
                                conditions: ConditionsType[Message.AfterUnitBecomeDefender]=[],
                                ) -> 'Ability':

        def check_by_face(effect: 'Effect', message: 'Message.AfterUnitBecomeDefender') -> bool:
            if by_effect_face == None:
                return True
            return Condition.CheckWhichCard(by_effect_face, message.by_effect.this, effect)

        # def check_on_event(effect: 'Effect', message: 'Send.AfterUnitBecomeDefender') -> bool:
        #     if on_event == None:
        #         return True
        #     return isinstance(message.on_event, on_event)

        return Ability(
            ability_type,
            Message.AfterUnitBecomeDefender,
            [
                check_by_face,
                # check_on_event,
                *conditions
            ],
            operation,
            is_local=by_effect_face == "This"
        )
