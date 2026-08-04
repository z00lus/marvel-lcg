from . import *

class AbilityFactoryResources:

    @staticmethod
    def DoubleResourcesThisGenerates(for_card: 'CardFinder',
                                    ) -> 'Ability':
        def the_power_of_leadership(effect: 'Effect', message: 'Message.CheckPlayerCanPayCost') -> 'Resources|None':
            from game.card.face.card_type import Resource
            from game.card.face.attribute.has_cost import HasCost

            this = effect.this.CastTo(Resource)
            Unused(this)

            res = this.printed_resource
            paying_for_card = message.paying_for_card
            if paying_for_card != None and \
                HasCost.IsType(paying_for_card) and \
                for_card.Check(paying_for_card) and \
                res.val <= message.cost.val:
                # and \
                # paying_card.has_printed_cost and \
                # message.for_effect.checker.cost_for_different_target.target_cost[None].cost.val > 0:
                # Fix "overpay", see https://itch.io/t/4958786/ant-man12011-and-the-power-of-leadership01072-bug
                res *= 2
            return res

        return AbilityFactoryResources.CheckThisCanDropPay(
            the_power_of_leadership,
        )

    @staticmethod
    def CheckThisCanDropPay(resources_fn: Callable[['Effect', 'Message.CheckPlayerCanPayCost'], 'Resources|None']|Resources|None=None,
                            for_card: 'CardFinder|None'=None,
                            *,
                            spend_this_only_in_hero_form: bool|None=None,
                            ) -> 'Ability':
        from game.card.face.card_type import Event

        def check_can_pay(effect: 'Effect', message: 'Message.CheckPlayerCanPayCost') -> bool:
            this = effect.this
            if not this.IsLikeInHand():
                return False
            if Event.IsType(message.paying_for_effect.this):
                if message.paying_for_effect.this.alliance:
                    return True
            if any(x.IsName("Coordinated Effort") for x in message.paying_for_effect.this.GetAttachedUpgrades()):
                return True
            if effect.ability.CheckAnyPlayerCanTriggerThis(effect):
                return True
            # HACK, TODO: clean this
            if this.card.area.bind_card and \
                this.card.area.bind_card.face.IsName("53021"):
                return True
            return this.card.area == message.GetToPlayer().hand_cards

        return AbilityFactoryResources.CheckThisCanPayCost(
            resources_fn,
            for_card,
            spend_this_only_in_hero_form=spend_this_only_in_hero_form,
            bind_ability=lambda face: face.effect.Find(func_name="DiscardPay")[0],
            conditions=[check_can_pay]
        ).SetFuncName("CheckThisCanDropPay")

    @staticmethod
    def CheckThisCanPayCost(resources_fn: Callable[['Effect', 'Message.CheckPlayerCanPayCost'], 'Resources|None']|Resources|None=None,
                            for_card: 'CardFinder|None'=None,
                            *,
                            for_ability: str|None=None,
                            spend_this_only_in_hero_form: bool|None=None,
                            for_card_from_hand: bool|None=None,
                            is_play_card: bool|None=None,
                            who_trigger_this_effect: Literal["You"]|None=None,
                            bind_ability: 'Callable[[CardFace], Effect]',
                            conditions: ConditionsType[Message.CheckPlayerCanPayCost]=[],
                            ) -> 'Ability':
        from game.card.face.base import ClassCard
        from game.card.face.card_type import Identity

        if resources_fn == None:
            def action(effect: 'Effect', message: 'Message2'):
                if ClassCard.IsType(effect.this):
                    return effect.this.printed_resource
                else:
                    return Resources("0")
            resources_fn = action
        elif isinstance(resources_fn, Resources):
            res = resources_fn
            resources_fn = lambda effect, message: res

        def check_is_not_the_target(effect: 'Effect', messsage: 'Message.CheckPlayerCanPayCost') -> bool:
            # Fix "30001a"
            if effect.this.IsInPlay():
                return True
            return effect.this != messsage.paying_for_target

        def check_spend_this_only_in_hero_form(effect: 'Effect', messsage: 'Message.CheckPlayerCanPayCost') -> bool:
            if spend_this_only_in_hero_form == None:
                return True
            return effect.GetInitiator().IsHero()

        def check_for_card(effect: 'Effect', message: 'Message.CheckPlayerCanPayCost') -> bool:
            if for_card == None:
                return True
            return for_card.Check(message.paying_for_effect.this)

        def check_for_ability(effect: 'Effect', message: 'Message.CheckPlayerCanPayCost') -> bool:
            if for_ability == None:
                return True
            return for_ability == message.paying_for_effect.ability.name

        def check_for_card_from_hand(effect: 'Effect', message: 'Message.CheckPlayerCanPayCost') -> bool:
            if for_card_from_hand == None:
                return True
            return for_card_from_hand == message.paying_for_effect.this.IsLikeInHand()

        def check_is_play_card(effect: 'Effect', message: 'Message.CheckPlayerCanPayCost') -> bool:
            if is_play_card == None:
                return True
            return is_play_card ==  message.paying_for_effect.ability.is_play

        def check_who_trigger_this_effect(effect: 'Effect', message: 'Message.CheckPlayerCanPayCost') -> bool:
            if who_trigger_this_effect == None:
                return True
            if who_trigger_this_effect == "You":
                return effect.initiator == message.GetToPlayer()

        def check_generate_resources_type(effect: 'Effect', message: 'Message.CheckPlayerCanPayCost'):
            if effect.ability.IsFunction("CanGenerateResources"):
                for condition in Ability.GetAbilityTypeCondition(effect.ability.second_type):
                    if not condition(effect, message):
                        return False
            return True

        def check_cannot_generate_self(effect: 'Effect', message: 'Message.CheckPlayerCanPayCost'):
            this = effect.this
            if Identity.IsType(this):
                return True
            return effect.this != message.paying_for_effect.this

        # def check_can_pay(effect: 'Effect', message: 'Send.CheckPlayerCanPayingResources') -> None:
        #     res = resources_fn(effect, message)
        #     if res != 0 and effect.HasCostTargets():
        #         # message.UpdateCost(resources_fn(effect, message), effect)
        #         message.AddPayment(effect, Resources("0", reduce=res))

        def add_to_pay_list(effect: 'Effect', message: 'Message.CheckPlayerCanPayCost') -> None:
            # `effect` is check_can_pay
            # `message.paying_for_targets` is what to pay
            this = effect.this
            if isinstance(message, Message.WhenPlayerInTurn):
                return
            target = message.paying_for_targets[0] if message.paying_for_targets != [] else None

            need_cost = message.paying_for_effect.checker.cost_for_different_target.GetCost(target)
            assert need_cost
            if need_cost:
                if need_cost.rule.from_hand:
                    if not this.IsLikeInHand():
                        return

            # Hack
            player = message.GetToPlayer()
            effect.context.initiator = player

            res = resources_fn(effect, message)
            if res != None:
                res_message = Message.CheckEffectGeneratedResources(effect, message, res)
                res_message.Send()
                res = res_message.res
                if res.CanPayThisCost(need_cost) and effect.checker.HasCostTargets():
                    # if isinstance(bind_ability, Ability):
                    #     bind_effect = effect.this.effect.RegisterTempEffect(
                    #         bind_ability,
                    #         unregister_after_exec=False,
                    #     )
                    # else:
                    bind_effect = bind_ability(effect.this)
                    def repeat():
                        if effect.ability.available_times_fn == None:
                            return [bind_effect]
                        else:
                            return [bind_effect] * effect.ability.available_times_fn(effect, message)
                    found_effects = repeat()
                    for found_effect in found_effects:
                        # 1. Sometimes it will add multiple effects for the same effect,
                        # That's because that `for_effect` has different targets
                        # 2. Sometimes the target nums are double
                        # It's because of "12024"
                        message.AddPayment(found_effect, res, effect)
                    pass
                pass

        return Ability(
            AbilityType.CheckResource,
            Message.CheckPlayerCanPayCost,
            [
                check_cannot_generate_self,
                check_generate_resources_type,
                check_is_not_the_target,
                check_spend_this_only_in_hero_form,
                check_for_card,
                check_for_ability,
                check_for_card_from_hand,
                check_is_play_card,
                check_who_trigger_this_effect,
                *conditions
            ],
            add_to_pay_list,
            # local=True
        ).SetFuncName("CheckPay")

    # Check 31001a for `resources_fn`, `DoGenerateResources`
    @staticmethod
    def CanGenerateResources(ability_type: 'Literal[AbilityType.Resource, AbilityType.HeroResource, AbilityType.AlterEgoResource]',
                            resources: 'Resources|None'=None,
                            for_card: 'CardFinder|None'=None,
                            *,
                            resources_fn: 'Callable[[Effect, Message.CheckPlayerCanPayCost], Resources|None]|None'=None,
                            # bind_ability: 'Ability|None'=None,
                            # *,
                            for_ability: str|None=None,
                            from_hand: bool|None=None,
                            for_player_whose_identity_has_trait: "CardFace.TRAITS|None"=None,
                            is_play_card: bool|None=None,
                            who_trigger_this_effect: Literal["You"]|None=None,
                            conditions: ConditionsType[Message.CheckPlayerCanPayCost]=[],
                            ex_operation: OperationType[Message.WhenPlayerPayingResources]|None=None,
                            ) -> 'Ability':
        from game.card.face.card_type import Event

        if resources_fn == None:
            assert resources != None
            resources_fn = lambda effect, message: resources

        def check_can_pay(effect: 'Effect', message: 'Message.CheckPlayerCanPayCost') -> bool:
            if not effect.this.IsInPlay():
                return False
            if Event.IsType(message.paying_for_effect.this):
                if message.paying_for_effect.this.alliance:
                    return True
            if any(x.IsName("Coordinated Effort") for x in message.paying_for_effect.this.GetAttachedUpgrades()):
                return True
            # Hack
            player = message.GetToPlayer()
            effect.context.initiator = player

            if effect.ability.CheckAnyPlayerCanTriggerThis(effect):
                return True

            if for_player_whose_identity_has_trait:
                return player.GetIdentity().HasTrait(for_player_whose_identity_has_trait)
            else:
                return player == effect.this.GetControlBy()

        ability = AbilityFactoryResources.CheckThisCanPayCost(
            resources_fn,
            for_card,
            conditions=[
                check_can_pay,
                *conditions
            ],
            for_ability=for_ability,
            for_card_from_hand=from_hand,
            is_play_card=is_play_card,
            who_trigger_this_effect=who_trigger_this_effect,
            bind_ability=lambda face: face.effect.Find(func_name="DoGenerateResources")[0]
        ).SetFuncName("CanGenerateResources") \
        .SetSecondType(ability_type) \
        .SetGenerateResourcesExOperation(ex_operation)

        if for_player_whose_identity_has_trait:
            ability.AnyPlayerCanDoThis(player_identity_has_trait=for_player_whose_identity_has_trait)

        return ability

    @staticmethod
    def UpdateResourcesGeneratedWhilePlayingThis(*,
                                                 color: "Resources.RBYG",
                                                 update_rule: 'Literal["Double"]|Resources') -> 'Ability':
        def UpdateGenerateResources(effect: 'Effect', message: 'Message.CheckEffectGeneratedResources'):
            if update_rule == "Double":
                message.SetResources(message.res + Resources(color) * message.res.GetColor(color, convert_green_res=False), effect)
            else:
                message.SetResources(message.res + update_rule, effect)
        
        return Ability(
            AbilityType.NonKeyword,
            Message.CheckEffectGeneratedResources,
            [
                lambda effect, message:
                    effect.this == message.for_effect.this and \
                    message.res.HasColorPrinted(color)
            ],
            lambda effect, message:
                UpdateGenerateResources(effect, message),
            is_local=True
        ).CanWorkOnlyInHand()

    # Do
    @staticmethod
    def DoDiscardThisToGenerateResources(ability_type: 'AbilityType',
                                        *,
                                        res_fn: Callable[['Effect', 'Message.WhenPlayerPayingResources'], 'Resources']|None=None,
                                        # condition: ConditionType[Message.WhenPlayerPayingResources]|None=None,
                                        ex_operation: OperationType[Message.WhenPlayerPayingResources]|None=None,
                                        ) -> 'Ability':

        def move_this_to_resources_area(targets: Sequence['CardFace'], effect: 'Effect') -> bool:
            from game.operate.faces import Faces
            this = effect.this
            area_resources = this.GetControlByPlayer().area_resources
            return Faces.MoveAllTo([this], area_resources, effect) == [this]

        return AbilityFactoryResources.DoGenerateResources(
            ability_type,
            "This",
            res_fn=res_fn,
            conditions=[
                lambda effect, message:
                    effect.this != message.for_effect.this
            ],
            ex_operation=ex_operation,
        ).SetFuncName("DiscardPay").SetCostFunc(CostFunc.Custom(None, move_this_to_resources_area))

    @staticmethod
    def DoGenerateResources(ability_type: 'AbilityType',
                            which_card: Literal["This"],
                            *,
                            res_fn: Callable[['Effect', 'Message.WhenPlayerPayingResources'], 'Resources']|None=None,
                            conditions: ConditionsType[Message.WhenPlayerPayingResources]=[],
                            ex_operation: OperationType[Message.WhenPlayerPayingResources]|None=None,
                            ) -> 'Ability':

        def generate_resource(effect: 'Effect', message: 'Message.WhenPlayerPayingResources') -> None:
            this = effect.this
            if res_fn:
                res = res_fn(effect, message)
            else:
                res = message.expected_res
            message.SetGenerateRes(res)
            for cost_func in message.cost_check_effect.cost_func.GetAll():
                if not cost_func.PayCost(effect, effect.GetInitiator()):
                    if message.GetToPlayer().is_eliminated:
                        return
                    from game.exceptions.exceptions import GameSignal_UndoRequest
                    raise GameSignal_UndoRequest()
            assert res.val > 0 or res.reduce > 0, f"{res=}"
            message.GetToPlayer().res_pool.Gain(res, effect)
            res_message = Message.WhenCardBeSpendAsResource(this, res, message.for_effect, effect.GetInitiator())
            res_message.Send()
            if ex_operation:
                ex_operation(effect, message)

        def check_which_card(effect: 'Effect', message: 'Message.WhenPlayerPayingResources') -> bool:
            if which_card == "This":
                return effect == message.by_effect

        return Ability(
            ability_type,
            Message.WhenPlayerPayingResources,
            [
                # effect.this.GetPlayer() == message.to_player and \
                check_which_card,
                *conditions
            ],
            generate_resource,
            is_local=which_card == "This",
        ).SetFuncName("DoGenerateResources")

    ################################################################################
    #
    @staticmethod
    def WhenCalculateEffectCost(ability_type: 'AbilityType',
                                operation: OperationType[Message.WhenCalculateEffectCost],
                                *,
                                conditions: ConditionsType[Message.WhenCalculateEffectCost],
                                is_local: bool|None=None,
                                ) -> 'Ability':
        def action_fn(effect: 'Effect', message: 'Message.WhenCalculateEffectCost') -> None:
            message.check_effect.this.card.ui.cost.Add(effect, effect.this)
            operation(effect, message)

        return Ability(
            ability_type,
            Message.WhenCalculateEffectCost,
            conditions,
            action_fn,
            is_local=is_local
        )

    @staticmethod
    def IgnoreThisCostIf(ability_type: 'AbilityType',
                         your_identity_has_trait: "CardFace.TRAITS|None"=None,
                         *,
                         conditions: ConditionsType[Message.WhenCalculateEffectCost]=[]
                         ) -> 'Ability':

        def ignore_cost(effect: 'Effect', message: 'Message.WhenCalculateEffectCost') -> None:
            message.IgnoreResourceCost(effect)

        def check_your_identity_has_trait(effect: 'Effect', message: 'Message2') -> bool:
            if your_identity_has_trait == None:
                return True
            initiator = effect.GetInitiator()
            identity = initiator.GetIdentity()
            return identity.HasTrait(your_identity_has_trait)

        return AbilityFactoryResources.WhenCalculateEffectCost(
            ability_type,
            ignore_cost,
            conditions=[
                lambda effect, message:
                    effect.this == message.check_effect.this and \
                    message.is_play,
                check_your_identity_has_trait,
                *conditions,
            ],
        ).NoOutOfPlayLimit()

    @staticmethod
    def EachCardYouPlayCostAdditionalResource(which_card: Type['TC']|None,
                                              update_cost: int) -> 'Ability':
        def act_update_cost(effect: 'Effect', message: 'Message.WhenCalculateEffectCost') -> None:
            message.UpdateCost(update_cost, effect)
        
        def check_which_card(effect: 'Effect', message: 'Message.WhenCalculateEffectCost') -> bool:
            if which_card == None:
                return True
            # assert message.check_effect.this != None
            return which_card.IsType(message.check_effect.this)

        return AbilityFactoryResources.WhenCalculateEffectCost(
            AbilityType.NonKeyword,
            act_update_cost,
            conditions=[
                lambda effect, message:
                    effect.this.bind_face != None and \
                    message.is_play and \
                    effect.this.GetBindFace().GetControlBy() == message.GetToPlayer(),
                check_which_card,
            ],
        ).NoOutOfPlayLimit()

    @staticmethod
    def AfterYouSpendThisCard(ability_type: 'AbilityType',
                            operation: OperationType[Message.AfterCardsBeSpendAsResource],
                            *,
                            to_pay_card: 'CardFinder|None'=None,
                            conditions: ConditionsType[Message.AfterCardsBeSpendAsResource]=[],
                            is_in_hero_from: "CardFace.TRAITS|None"=None,
                            identity_has_trait: "CardFace.TRAITS|None"=None,
                            ) -> 'Ability':

        def check_which_card(effect: 'Effect', message: 'Message.AfterCardsBeSpendAsResource') -> bool:
            return effect.this in message.faces

        def check_is_in_hero_from(effect: 'Effect', message: 'Message.AfterCardsBeSpendAsResource') -> bool:
            if is_in_hero_from == None:
                return True
            return Condition.YouAreInHeroFrom(effect, is_in_hero_from)

        def check_identity_has_trait(effect: 'Effect', message: 'Message.AfterCardsBeSpendAsResource') -> bool:
            if identity_has_trait == None:
                return True
            return effect.GetInitiator().GetRoleCharacter().HasTrait(identity_has_trait)

        def check_to_pay_card(effect: 'Effect', message: 'Message.AfterCardsBeSpendAsResource') -> bool:
            if to_pay_card == None:
                return True
            return message.pay_for_card != None and to_pay_card.Check(message.pay_for_card)

        return Ability(
            ability_type,
            Message.AfterCardsBeSpendAsResource,
            [
                check_which_card,
                check_is_in_hero_from,
                check_identity_has_trait,
                check_to_pay_card,
                *conditions
            ],
            operation,
            is_local=True,
        ).NoOutOfPlayLimit()

    @staticmethod
    def WhenYouSpendThisCardToPlay(ability_type: 'AbilityType',
                                   operation: OperationType[Message.WhenCardBeSpendAsResource],
                                   to_pay_card: 'CardFinder|None'=None,
                                   ) -> 'Ability':
        def check_played_card(effect: 'Effect', message: 'Message.WhenCardBeSpendAsResource') -> bool:
            if to_pay_card == None:
                return True
            return message.pay_for_card != None and to_pay_card.Check(message.pay_for_card)

        return Ability(
            ability_type,
            Message.WhenCardBeSpendAsResource,
            [
                Condition2.ThisIsTrigger,
                check_played_card,
            ],
            operation
        ).NoOutOfPlayLimit()

    # @staticmethod
    # def ReduceCostToPlayCard(value: int,
    #                         which_card: CardType,
    #                         *,
    #                         which_player: 'Player|Literal["Attached", "You"]|None'=None,
    #                         conditions: ConditionsType[Message.WhenCalculateEffectCost]=[],
    #                         ) -> 'Ability':

    #     return AbilityFactoryResources.UpdateCostOfCard(
    #         value * -1,
    #         which_card,
    #         which_player=which_player,
    #         is_play=True,
    #         conditions=conditions,
    #     )

    @staticmethod
    def ReduceCostToPlayThis(update_cost_fn: Callable[['Effect'], int]|int,
                            *,
                            which_effect: 'Effect|None'=None,
                            your_identity_has_traits: Sequence["CardFace.TRAITS"]=[],
                            each_card_you_control: 'CardFinder|None'=None,
                            each_minion_engaged_with_you: bool=False,
                            conditions: ConditionsType[Message.WhenCalculateEffectCost]=[],
                            ) -> 'Ability':

        def check_your_identity_has_traits(effect: 'Effect', message: 'Message.WhenCalculateEffectCost') -> bool:
            if your_identity_has_traits == []:
                return True
            identity = effect.GetInitiator().GetIdentity()
            return identity.HasTrait(*your_identity_has_traits)

        def check_each_card_you_control(effect: 'Effect', message: 'Message.WhenCalculateEffectCost') -> bool:
            initiator = effect.GetInitiator()
            return Condition.CheckWhichCard(each_card_you_control, initiator.GetControlCards(), effect)

        def check_each_minion_engaged_with_you(effect: 'Effect', message: 'Message.WhenCalculateEffectCost') -> bool:
            if not each_minion_engaged_with_you:
                return True
            initiator = effect.GetInitiator()
            return not not initiator.GetEngagedMinions()

        def update_cost(effect: 'Effect') -> int:
            base_val = 1

            if each_card_you_control:
                initiator = effect.GetInitiator()
                base_val = len(initiator.GetControlCards(each_card_you_control))

            if each_minion_engaged_with_you:
                initiator = effect.GetInitiator()
                base_val = len(initiator.GetEngagedMinions())

            if isinstance(update_cost_fn, int):
                value = base_val * update_cost_fn
            else:
                value = base_val * update_cost_fn(effect)
            return value

        return AbilityFactoryResources.ReduceCostToPlayFaceWhen(
            "This",
            update_cost,
            "AnyPlayer",
            which_effect=which_effect,
            conditions=[
                check_your_identity_has_traits,
                check_each_card_you_control,
                check_each_minion_engaged_with_you,
                *conditions
            ],
        )

    @staticmethod
    def ReduceCostToPlayFaceWhen(which_card: CardType,
                                update_cost_fn: Callable[['Effect'], int]|int,
                                which_player: 'Player|Literal["Attached", "You", "EachPlayer", "AnyPlayer"]',
                                *,
                                which_effect: 'Effect|None'=None,
                                conditions: ConditionsType[Message.WhenCalculateEffectCost]=[],
                                ) -> 'Ability':

        def update_cost(effect: 'Effect') -> int:
            base_val = 1

            if isinstance(update_cost_fn, int):
                value = base_val * update_cost_fn
            else:
                value = base_val * update_cost_fn(effect)
            return value * -1

        return AbilityFactoryResources.UpdateCostOfCardInternal(
            which_card,
            update_cost,
            which_player,
            which_effect=which_effect,
            is_play=True,
            conditions=conditions,
        )

    @staticmethod
    def IncreaseResourceCostToPlay(which_card: CardType,
                                    value: int,
                                    which_player: 'Player|Literal["Attached", "You", "EachPlayer", "AnyPlayer"]',
                                    *,
                                    conditions: ConditionsType[Message.WhenCalculateEffectCost]=[],
                                    ) -> 'Ability':
        return AbilityFactoryResources.UpdateCostOfCardInternal(
            which_card,
            value,
            which_player,
            is_play=True,
            conditions=conditions,
        )

    @staticmethod
    def UpdateCostOfCardInternal(which_card: CardType,
                                update_cost_fn: Callable[['Effect'], int]|int,
                                which_player: 'Player|Literal["Attached", "You", "EachPlayer", "AnyPlayer"]',
                                *,
                                which_effect: 'Effect|None'=None,
                                is_play: bool|None=None,
                                conditions: ConditionsType[Message.WhenCalculateEffectCost]=[],
                                ) -> 'Ability':
        from game.selector import Select

        def check_which_card(effect: 'Effect', message: 'Message.WhenCalculateEffectCost') -> bool:
            return Condition.CheckWhichCard(which_card, message.check_effect.this, effect)

        def check_which_effect(effect: 'Effect', message: 'Message.WhenCalculateEffectCost') -> bool:
            if which_effect == None:
                return True
            return which_effect == message.check_effect

        def check_which_player(effect: 'Effect', message: 'Message.WhenCalculateEffectCost') -> bool:
            if which_player == "AnyPlayer":
                return True
            if which_player == "EachPlayer":
                return True
            if which_player == "Attached":
                return effect.this.GetBindFace() == message.GetToPlayer().GetIdentity()
            if which_player == "You":
                return Select.GetYou(effect) == message.to_player
                # return message.check_effect.this.GetOwner() == message.to_player
            return which_player == message.to_player

        def check_is_play(effect: 'Effect', message: 'Message.WhenCalculateEffectCost') -> bool:
            if is_play == None:
                return True
            return is_play == message.is_play

        def reduce_cost(effect: 'Effect', message: 'Message.WhenCalculateEffectCost') -> None:
            base_val = 1

            if isinstance(update_cost_fn, int):
                value = base_val * update_cost_fn
            else:
                value = base_val * update_cost_fn(effect)
            message.UpdateCost(value, effect)

        ability = AbilityFactoryResources.WhenCalculateEffectCost(
            AbilityType.NonKeyword,
            reduce_cost,
            conditions=[
                check_which_card,
                check_which_effect,
                check_which_player,
                check_is_play,
                *conditions,
            ],
            is_local=which_card == "This"
        )
        if which_card == "This":
            ability.NoOutOfPlayLimit()
        return ability

    @staticmethod
    def AfterGenerateResources(ability_type: 'AbilityType',
                                which_player: PlayerType,
                                operation: OperationType[Message.WhenCardBeSpendAsResource],
                                conditions: ConditionsType[Message.WhenCardBeSpendAsResource]=[],
                                ) -> 'Ability':

        def check_which_player(effect: 'Effect', message: 'Message.WhenCardBeSpendAsResource') -> bool:
            return Condition.CheckWhichPlayer(which_player, message.GetToPlayer(), effect)

        return Ability(
            ability_type,
            Message.WhenCardBeSpendAsResource,
            [
                check_which_player,
                *conditions
            ],
            operation
        )
