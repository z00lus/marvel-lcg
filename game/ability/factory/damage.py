from . import *

class AbilityFactoryDamage:

    @staticmethod
    def WhenUnitWouldTakeDamage(ability_type: 'AbilityType',
                                who_take_damage: CardType|Literal["You"],
                                operation: OperationType[Message.WhenUnitWouldTakeDamage],
                                *,
                                is_from_attack: bool|Message.WhenUnitWouldAttack|None=None,
                                # include_overkill: bool|None=None, # Set False when this effect includes `IncreaseDamage`
                                is_consequential_damage: bool|None=None,
                                while_defending: bool|None=None,
                                control_by: 'Player|None'=None,
                                who_deal_damage: CardType=None, # attacker
                                at_least_damage: int=1,
                                more_than_damage: int=0,
                                not_include_this_effect: bool|None=None,
                                conditions: ConditionsType[Message.WhenUnitWouldTakeDamage]=[],
                                ) -> 'Ability':

        def check_who_take_damage(effect: 'Effect', message: 'Message.WhenUnitWouldTakeDamage') -> bool:
            rule = Condition.GetYouRule(who_take_damage, identity=True)
            return Condition.CheckWhichCard(rule, message.trigger, effect)

        def check_is_from_attack(effect: 'Effect', message: 'Message.WhenUnitWouldTakeDamage') -> bool:
            if is_from_attack == None:
                return True
            if isinstance(is_from_attack, Message2):
                return is_from_attack == message.would_atk_message
            return is_from_attack == message.IsFromAttack()

        # def check_is_from_overkill(effect: 'Effect', message: 'Message.WhenUnitWouldTakeDamage') -> bool:
        #     if include_overkill == None:
        #         return True
        #     return include_overkill == message.would_deal_damage_message.IsOverkill()

        def check_is_consequential_damage(effect: 'Effect', message: 'Message.WhenUnitWouldTakeDamage') -> bool:
            if is_consequential_damage == None:
                return True
            from game.effect.rule import Consequential
            return type(message.would_deal_damage_message.by_effect) is Consequential

        def check_while_defending(effect: 'Effect', message: 'Message.WhenUnitWouldTakeDamage') -> bool:
            if while_defending == None:
                return True
            if while_defending == True:
                return message.being_atk_message != None and \
                    message.trigger == message.being_atk_message.defender
            else:
                return message.being_atk_message == None or \
                    message.trigger != message.being_atk_message.defender

        def check_control_by(effect: 'Effect', message: 'Message.WhenUnitWouldTakeDamage') -> bool:
            if control_by == None:
                return True
            return control_by == message.trigger.GetControlBy()

        def check_not_include_this_effect(effect: 'Effect', message: 'Message.WhenUnitWouldTakeDamage') -> bool:
            if not_include_this_effect == None:
                return True
            assert not_include_this_effect == True
            return effect != message.by_effect

        def check_who_deal_damage(effect: 'Effect', message: 'Message.WhenUnitWouldTakeDamage') -> bool:
            return Condition.CheckWhichCard(who_deal_damage, message.source, effect)

        return Ability(
            ability_type,
            Message.WhenUnitWouldTakeDamage,
            [
                lambda effect, message:
                    not message.IsBePrevent() and \
                    message.will_take_damage >= at_least_damage and \
                    message.will_take_damage > more_than_damage,
                check_who_take_damage,
                check_is_from_attack,
                check_while_defending,
                # check_is_from_overkill,
                check_who_deal_damage,
                check_is_consequential_damage,
                check_control_by,
                check_not_include_this_effect,
                *conditions,
            ],
            operation,
            is_local=who_take_damage == "This" or who_deal_damage == "This"
        )

    @staticmethod
    def AfterUnitTookDamage(ability_type: 'AbilityType',
                            who_took_damage: CardType|Literal["You"],
                            operation: OperationType[Message.AfterUnitTookDamage],
                            *,
                            is_from_attack: bool|Message.WhenUnitWouldAttack|None=None, # will auto include overkill
                            is_indirect_damage: bool|None=None,
                            who_dealt_damage: CardType=None,
                            conditions: ConditionsType[Message.AfterUnitTookDamage]=[],
                            ) -> 'Ability':

        def check_who_took_damage(effect: 'Effect', message: 'Message.AfterUnitTookDamage') -> bool:
            rule = Condition.GetYouRule(who_took_damage, identity=True)
            return Condition.CheckWhichCard(rule, message.trigger, effect)

        def check_is_from_attack(effect: 'Effect', message: 'Message.AfterUnitTookDamage') -> bool:
            if is_from_attack == None:
                return True
            if isinstance(is_from_attack, Message2):
                return is_from_attack == message.would_atk_message
            return is_from_attack == message.IsFromAttack()

        def check_who_dealt_damage(effect: 'Effect', message: 'Message.AfterUnitTookDamage') -> bool:
            return Condition.CheckWhichCard(who_dealt_damage, message.source, effect)

        def check_is_indirect_damage(effect: 'Effect', message: 'Message.AfterUnitTookDamage') -> bool:
            if is_indirect_damage == None:
                return True
            return is_indirect_damage == message.IsIndirectDamage()


        return Ability(
            ability_type,
            Message.AfterUnitTookDamage,
            [
                lambda effect, message:
                    message.took_damage > 0,
                check_who_took_damage,
                check_is_from_attack,
                check_who_dealt_damage,
                check_is_indirect_damage,
                *conditions
            ],
            operation,
            is_local=who_took_damage == "This" or who_dealt_damage == "This"
        )

    @staticmethod
    def AfterYouDealDamage(ability_type: 'AbilityType',
                           dealt_to_who: CardType,
                           operation: OperationType[Message.AfterFaceDealDamage],
                           *,
                           conditions: ConditionsType[Message.AfterFaceDealDamage]=[],
                           ) -> 'Ability':
        return AbilityFactoryDamage.AfterFaceDealDamage(
            ability_type,
            "YourIdentity",
            dealt_to_who,
            operation,
            conditions=conditions
        )

    @staticmethod
    def AfterUnitDealExcessDamage(ability_type: 'AbilityType',
                                    which_card: CardType|Literal["You"],
                                    operation: OperationType[Message.AfterUnitDefeatedUnit],
                                    *,
                                    to_target: CardType=None,
                                    by_effect: 'Effect|None'=None,
                                    conditions: ConditionsType[Message.AfterUnitDefeatedUnit]=[],
                                    ) -> 'Ability':

        def check_who(effect: 'Effect', message: 'Message.AfterUnitDefeatedUnit') -> bool:
            rule = Condition.GetYouRule(which_card, identity=True)
            return Condition.CheckWhichCard(rule, message.killer, effect)

        def check_to_target(effect: 'Effect', message: 'Message.AfterUnitDefeatedUnit') -> bool:
            return Condition.CheckWhichCard(to_target, message.target, effect)

        def check_by_effect(effect: 'Effect', message: 'Message.AfterUnitDefeatedUnit') -> bool:
            if by_effect:
                return by_effect == message.by_effect
            return True

        return Ability(
            ability_type,
            Message.AfterUnitDefeatedUnit,
            [
                lambda effect, message:
                    message.excess_damage > 0,
                check_who,
                check_to_target,
                check_by_effect,
                *conditions,
            ],
            operation,
            is_local=which_card == "This" or to_target == "This"
        )

    @staticmethod
    def UnitCannotTakeMoreDamageEachPhase(ability_type: 'AbilityType',
                                        which_card: Literal["This"],
                                        cannot_take_more_than_damage: int
                                        ) -> 'Ability':
        from game.operate.effects import Effects
        from game.ability.factory import AbilityFactory

        def nimrod(effect: 'Effect', message: 'Message2') -> None:
            this = effect.this

            damage = 0
            temp_effects: List['Effect'] = []

            def reset_damage(effect: 'Effect', message: 'Message2'):
                nonlocal damage
                damage = 0
            temp_effects += this.effect.RegisterTemp(
                AbilityFactory.WhenPhaseBegin(
                    AbilityType.NonKeyword,
                    None,
                    reset_damage
                ),
                unregister_after_exec=False
            )

            def add_damage(effect: 'Effect', message: 'Message.AfterUnitTookDamage'):
                nonlocal damage
                damage += message.took_damage
            temp_effects += this.effect.RegisterTemp(
                AbilityFactory.AfterUnitTookDamage(
                    AbilityType.Temp0,
                    "This",
                    add_damage,
                ),
                unregister_after_exec=False
            )

            temp_effects += this.effect.RegisterTemp(
                AbilityFactory.UnitCannotTakeDamageWhile(
                    AbilityType.NonKeyword,
                    "This",
                    cannot_take_more_than_damage=lambda effect:
                        cannot_take_more_than_damage - damage
                ),
                unregister_after_exec=False
            )

            def clean(effect: 'Effect', message: 'Message2'):
                Effects.UnRegister(temp_effects)
            this.effect.RegisterTemp(
                AbilityFactory.WhenCardLeavePlay(
                    AbilityType.NonKeyword,
                    "This",
                    clean,
                ),
                unregister_after_exec=True
            )

        return AbilityFactory.AfterCardEnterPlay(
            ability_type,
            which_card,
            nimrod
        )

    @staticmethod
    def UnitCannotTakeDamage(which_card: CardTypeMin) -> 'Ability':
        return AbilityFactory.GiveBuffToInPlayWhenApplyThis(
            which_card,
            buffs=[BuffCannotTakeDamage]
        )

    @staticmethod
    def UnitCannotTakeDamageWhile(ability_type: 'AbilityType',
                                  which_card: CardType|Literal["You"],
                                  *,
                                  conditions: ConditionsType[Message.WhenUnitWouldTakeDamage]=[],
                                  is_damage_more_than: Callable[['Effect'], int]|int|None=None,
                                  is_from_attack: bool|Message.WhenUnitWouldAttack|None=None,
                                  cannot_take_more_than_damage: Callable[['Effect'], int]|int|None=None, # not prevent all
                                  while_face_is_in_play: 'CardFinder|None'=None,
                                  damage_from: CardType=None,
                                  ) -> 'Ability':
        from game.operate.worlds import Worlds

        if cannot_take_more_than_damage:
            assert is_damage_more_than == None
            is_damage_more_than = cannot_take_more_than_damage

        def cannot_take_damage(effect: 'Effect', message: 'Message.WhenUnitWouldTakeDamage') -> None:
            if cannot_take_more_than_damage != None:
                if isinstance(cannot_take_more_than_damage, int):
                    value = cannot_take_more_than_damage
                else:
                    value = cannot_take_more_than_damage(effect)
                message.SetCannotTakeMoreThanDamage(value, effect)
            else:
                message.PreventDamage("All", effect)

        def check_while_face_is_in_play(effect: 'Effect', message: 'Message.WhenUnitWouldTakeDamage') -> bool:
            if while_face_is_in_play == None:
                return True

            for face in Worlds.GetOnFieldCards(effect):
                if while_face_is_in_play.Check(face):
                    return True
            return False

        def check_is_damage_more_than(effect: 'Effect', message: 'Message.WhenUnitWouldTakeDamage') -> bool:
            if is_damage_more_than == None:
                return True
            if isinstance(is_damage_more_than, int):
                value = is_damage_more_than
            else:
                value = is_damage_more_than(effect)
            return message.will_take_damage > value

        # def damage_is_not_from_this(effect: 'Effect', message: 'Message.WhenUnitWouldTakeDamage') -> bool:
        #     return effect.this != message.by_effect.this

        def check_damage_from(effect: 'Effect', message: 'Message.WhenUnitWouldTakeDamage') -> bool:
            if damage_from == None:
                return True
            return Condition.CheckWhichCard(damage_from, message.by_effect.this, effect)

        return AbilityFactoryDamage.WhenUnitWouldTakeDamage(
            ability_type,
            which_card,
            cannot_take_damage,
            is_from_attack=is_from_attack,
            conditions=[
                check_is_damage_more_than,
                # damage_is_not_from_this,
                check_damage_from,
                check_while_face_is_in_play,
                *conditions,
            ],
        )

    @staticmethod
    def UnitCannotHaveMoreThanSustainedDamage(which_card: CardType|Literal["You"],
                                            *,
                                            more_than_sustained_damage: Callable[['Effect'], int]|Literal["6*", "12*", "18*"],
                                            conditions: ConditionsType[Message.WhenUnitWouldTakeDamage]=[],
                                            ) -> 'Ability':
        from game.operate.worlds import Worlds

        def cannot_take_damage(effect: 'Effect', message: 'Message.WhenUnitWouldTakeDamage') -> None:
            # message.SetCannotTakeMoreThanDamage(cannot_take_more_than_damage, effect)
            if isinstance(more_than_sustained_damage, str):
                damage = Worlds.ConvertPerPlayerIconToInt(more_than_sustained_damage, effect)
            else:
                damage = more_than_sustained_damage(effect)
            message.SetCannotHaveMoreThanSustained(damage, effect)

        return AbilityFactoryDamage.WhenUnitWouldTakeDamage(
            AbilityType.NonKeyword,
            which_card,
            cannot_take_damage,
            conditions=conditions,
        )

    @staticmethod
    def PreventAllDamageTo(which_card: CardType,
                           *,
                           conditions: ConditionsType[Message.WhenUnitWouldTakeDamage]=[]):
        def action(effect: 'Effect', message: 'Message.WhenUnitWouldTakeDamage') -> None:
            message.PreventDamage("All", effect)
        return AbilityFactoryDamage.WhenUnitWouldTakeDamage(
            AbilityType.NonKeyword,
            which_card,
            action,
            conditions=conditions
        )

    @staticmethod
    def ReduceCharacterTakeDamageBy(who_take_damage: CardType,
                                    num: int,
                                    *,
                                    this_attached_unit_only: Literal[True]|None=None,
                                    from_each_attack: bool|None=None,
                                    who_deal_damage: CardType=None,
                                    conditions: ConditionsType[Message.WhenUnitWouldTakeDamage]=[],
                                    ) -> 'Ability':
        def check_attached_unit_only(effect: 'Effect', message: 'Message.WhenUnitWouldTakeDamage') -> bool:
            if this_attached_unit_only == None:
                return True
            return Condition.ThisAttachedTo(effect, message.trigger)

        return AbilityFactoryDamage.WhenUnitWouldTakeDamage(
            AbilityType.NonKeyword,
            who_take_damage,
            lambda effect, message:
                message.ReduceDamage(num, effect),
            is_from_attack=from_each_attack,
            who_deal_damage=who_deal_damage,
            conditions=[
                check_attached_unit_only,
                *conditions
            ]
        )

    @staticmethod
    def UnitTakeAdditionalDamageFromCards(which_card: CardType,
                                        update_rule: Literal["Double", "Prevent"]|int,
                                        by_face: 'CardFinder|None'=None,
                                    #   *,
                                    #   has_printed_res: 'Resources.RBY|None'=None,
                                    #   non_printed_res: 'Resources.RBY|None'=None,
                                      ) -> 'Ability':
        from game.card.face.base import ClassCard
        def action(effect: 'Effect', message: 'Message.WhenUnitWouldTakeDamage') -> None:
            if isinstance(update_rule, int):
                if update_rule > 0:
                    message.IncreaseDamage(update_rule, effect)
                else:
                    assert False
                    message.ReduceDamage(update_rule, effect)
            elif update_rule == "Double":
                message.IncreaseDamage(message.will_take_damage, effect)
            elif update_rule == "Prevent":
                message.PreventDamage("All", effect)

        def condition(effect: 'Effect', message: 'Message.WhenUnitWouldTakeDamage') -> bool:
            if ClassCard.IsType(message.by_effect.this):
                # Ally attack should also trigger
                # if not message.by_effect.ability.is_play:
                #     return False
                if by_face == None:
                    return True
                return by_face.Check(message.by_effect.this)
            return False

        return AbilityFactoryDamage.WhenUnitWouldTakeDamage(
            AbilityType.NonKeyword,
            which_card,
            action,
            conditions=[
                condition
            ]
        )

    @staticmethod
    def UpdateAttacksDealDamage(*,
                                deal_damage_from: CardType=None,
                                with_piercing: bool|None=None,
                                deal_damage_to: CardType=None,
                                update_damage_rule: Literal["Double"]|int=0) -> 'Ability':
        def check_with_piercing(effect: 'Effect', message: 'Message.WhenCalculateAttackDamage') -> bool:
            if with_piercing != None:
                return with_piercing == message.would_atk_message.property.piercing
            return True

        def check_deal_damage_from(effect: 'Effect', message: 'Message.WhenCalculateAttackDamage') -> bool:
            return Condition.CheckWhichCard(deal_damage_from, message.attacker, effect)

        def check_deal_damage_to(effect: 'Effect', message: 'Message.WhenCalculateAttackDamage') -> bool:
            return Condition.CheckWhichCard(deal_damage_to, message.target, effect)

        def gain_attack_damage(effect: 'Effect', message: 'Message.WhenCalculateAttackDamage') -> None:
            if update_damage_rule == "Double":
                damage = message.will_take_damage
                return message.IncreaseDamage(damage, effect)
            else:
                assert update_damage_rule > 0
                return message.IncreaseDamage(update_damage_rule, effect)

        return Ability(
            AbilityType.NonKeyword,
            Message.WhenCalculateAttackDamage,
            [
                check_deal_damage_from,
                check_deal_damage_to,
                check_with_piercing,
            ],
            gain_attack_damage,
            is_local=deal_damage_to == "This" or deal_damage_from == "This"
        )

    @staticmethod
    def WhenDamageWouldBeDealtTo(ability_type: 'AbilityType',
                                who_take_damage: CardType|Literal["You"],
                                operation: OperationType[Message.WhenFaceWouldDealDamage],
                                *,
                                who_deal_damage: CardType=None,
                                conditions: ConditionsType[Message.WhenFaceWouldDealDamage]=[],
                                by_which_effect: 'Effect|None'=None,
                                by_play_card: CardType=None,
                                allow_zero_damage: bool=False,
                                is_undefended_attack: bool|None=None,
                                ) -> 'Ability':
        return AbilityFactoryDamage.WhenFaceWouldDealDamage(
            ability_type,
            who_deal_damage,
            operation,
            who_take_damage=who_take_damage,
            from_attack=None,
            include_overkill=True,
            conditions=conditions,
            by_which_effect=by_which_effect,
            by_play_card=by_play_card,
            allow_zero_damage=allow_zero_damage,
            is_undefended_attack=is_undefended_attack,
        )

    @staticmethod
    def WhenFaceWouldDealDamage(ability_type: 'AbilityType',
                                who_deal_damage: CardType|Literal["You"],
                                operation: OperationType[Message.WhenFaceWouldDealDamage],
                                *,
                                who_take_damage: CardType|Literal["You"]=None,
                                from_attack: bool|None=None,
                                include_overkill: bool=False, # ignore when `from_attack`
                                conditions: ConditionsType[Message.WhenFaceWouldDealDamage]=[],
                                by_which_effect: 'Effect|None'=None,
                                by_play_card: CardType=None,
                                allow_zero_damage: bool=False,
                                is_undefended_attack: bool|None=None, # Must be an attack
                                ) -> 'Ability':

        def check_who_deal_damage(effect: 'Effect', message: 'Message.WhenFaceWouldDealDamage') -> bool:
            rule = Condition.GetYouRule(who_deal_damage, identity=True)
            return Condition.CheckWhichCard(rule, message.attacker, effect)

        def check_who_take_damage(effect: 'Effect', message: 'Message.WhenFaceWouldDealDamage') -> bool:
            rule = Condition.GetYouRule(who_take_damage, identity=True)
            return Condition.CheckWhichCard(rule, message.target, effect)

        def check_is_from_attack(effect: 'Effect', message: 'Message.WhenFaceWouldDealDamage') -> bool:
            if from_attack == None:
                return check_is_from_overkill(effect, message)
            return from_attack == (message.would_atk_message != None)

        def check_by_which_effect(effect: 'Effect', message: 'Message.WhenFaceWouldDealDamage') -> bool:
            if by_which_effect == None:
                return True
            return by_which_effect == message.by_effect

        def check_is_from_overkill(effect: 'Effect', message: 'Message.WhenFaceWouldDealDamage') -> bool:
            if include_overkill == True:
                return True
            assert include_overkill == False
            return not message.IsOverkill()

        def check_by_play_card(effect: 'Effect', message: 'Message.WhenFaceWouldDealDamage') -> bool:
            if by_play_card == None:
                return True
            # if isinstance(message.by_effect, GameRule):
            if message.by_effect.is_rule:
                return False
            if not message.by_effect.ability.is_play:
                return False
            if message.IsBasicAttack():
                return False
            return Condition.CheckWhichCard(by_play_card, message.by_effect.this, effect)

        def check_allow_zero_damage(effect: 'Effect', message: 'Message.WhenFaceWouldDealDamage') -> bool:
            if allow_zero_damage:
                return True
            else:
                return message.damage > 0

        def check_is_undefended_attack(effect: 'Effect', message: 'Message.WhenFaceWouldDealDamage') -> bool:
            if is_undefended_attack == None:
                return True
            if message.would_atk_message == None:
                return False
            return is_undefended_attack == (message.would_atk_message.defender == None)

        return Ability(
            ability_type,
            Message.WhenFaceWouldDealDamage,
            [
                # lambda effect, message:
                #     not message.IsBePrevent() and \
                check_allow_zero_damage,
                check_who_deal_damage,
                check_who_take_damage,
                check_is_from_attack,
                check_by_which_effect,
                check_by_play_card,
                check_is_undefended_attack,
                *conditions
            ],
            operation,
            is_local=who_deal_damage == "This" or who_take_damage == "This" or by_play_card == "This"
        )

    @staticmethod
    def AfterFaceDealDamage(ability_type: 'AbilityType',
                            which_face_dealt_damage: CardType,
                            dealt_to_who: CardType,
                            operation: OperationType[Message.AfterFaceDealDamage],
                            *,
                            dealt_more_than_damage: int|None=None,
                            is_from_attack: bool|None=None,
                            conditions: ConditionsType[Message.AfterFaceDealDamage]=[],
                            ) -> 'Ability':
        def check_is_from_attack(effect: 'Effect', message: 'Message.AfterFaceDealDamage') -> bool:
            if is_from_attack == None:
                return True
            return is_from_attack == message.IsFromAttack()
    
        def check_who(effect: 'Effect', message: 'Message.AfterFaceDealDamage') -> bool:
            if which_face_dealt_damage == None:
                return True
            # Comment out this for "16037" and "16032"
            # if message.attacker == None:
            #     return False
            return Condition.CheckWhichCard(which_face_dealt_damage, message.trigger, effect)

        def check_dealt_to_who(effect: 'Effect', message: 'Message.AfterFaceDealDamage') -> bool:
            if dealt_to_who == None:
                return True
            return Condition.CheckWhichCard(dealt_to_who, message.who_took_damage, effect)

        def check_dealt_more_than_damage(effect: 'Effect', message: 'Message.AfterFaceDealDamage') -> bool:
            if dealt_more_than_damage == None:
                return True
            return message.dealt_damage >= dealt_more_than_damage

        return Ability(
            ability_type,
            Message.AfterFaceDealDamage,
            [
                lambda effect, message:
                    message.dealt_damage > 0,
                check_who,
                check_dealt_to_who,
                check_is_from_attack,
                check_dealt_more_than_damage,
                *conditions
            ],
            operation
        )

    @staticmethod
    def AfterFaceBeDealtDamage(ability_type: 'AbilityType',
                                which_face: CardType,
                                operation: OperationType[Message.WhenUnitWouldTakeDamage],
                                *,
                                conditions: ConditionsType[Message.WhenUnitWouldTakeDamage]=[],
                                ) -> 'Ability':

        return AbilityFactoryDamage.WhenUnitWouldTakeDamage(
            ability_type,
            which_face,
            operation,
            conditions=conditions,
            not_include_this_effect=True
        )

    ################################################################################
    # Cannot take damage
    @staticmethod
    def ThisCannotTakeDamageWhile(*,
                                conditions: ConditionsType[Message.WhenUnitWouldTakeDamage]|Literal[True]) -> 'Ability':

        if conditions == True:
            conditions = [lambda effect, message: True]

        return AbilityFactoryDamage.UnitCannotTakeDamageWhile(
            AbilityType.NonKeyword,
            "This",
            conditions=conditions,
        )

    @staticmethod
    def AfterDamageBePrevented(ability_type: 'AbilityType',
                                operation: OperationType[Message.AfterDamageBePrevented],
                                *,
                                who_not_take_damage: CardType=None,
                                prevent_by: CardType=None,
                                is_from_attack: bool|None=None,
                                damage_more_than: int|None=None,
                                conditions: ConditionsType[Message.AfterDamageBePrevented]=[],
                                ) -> 'Ability':

        def check_is_from_attack(effect: 'Effect', message: 'Message.AfterDamageBePrevented') -> bool:
            if is_from_attack == None:
                return True
            return is_from_attack == message.IsFromAttack()
    
        def check_who_not_take_damage(effect: 'Effect', message: 'Message.AfterDamageBePrevented') -> bool:
            return Condition.CheckWhichCard(who_not_take_damage, message.trigger, effect)
        
        def check_prevent_by(effect: 'Effect', message: 'Message.AfterDamageBePrevented') -> bool:
            return Condition.CheckWhichCard(prevent_by, message.prevent_by_effect.this, effect)

        def check_damage_more_than(effect: 'Effect', message: 'Message.AfterDamageBePrevented') -> bool:
            if damage_more_than == None:
                return True
            return message.prevent_damage >= damage_more_than

        return Ability(
            ability_type,
            Message.AfterDamageBePrevented,
            [
                *conditions,
                check_who_not_take_damage,
                check_prevent_by,
                check_damage_more_than,
                check_is_from_attack,
            ],
            operation
        )
