from core import *
from game.card.face import *
from game.ability import *
from game.message import *
from game.player import *
from game.element.cost import Cost
from engine.log import Log
from game.effect.effect_failure import EffectFailure

CATEGORY_NAME = "EFFECT"

class EffectChecker:
    def __init__(self, effect: 'Effect') -> None:
        from game.effect.effect_failure import FailureReason
        from game.effect.effect_target_cost import TargetCost
        self.effect = effect
        self.ability = effect.ability

        self.failures = FailureReason(effect)
        self.cost_for_different_target = TargetCost()

    def HasCostTargets(self) -> bool:
        for cost_func in self.effect.cost_func.GetAll():
            if not cost_func.HasTargets(self.effect):
                return False
        return True

    def IsChoiceOption(self) -> bool:
        effect = self.effect
        message = effect.bind_message
        if not isinstance(message, Message.WhenPlayerChooseAbility):
            return False
        source = message.by_effect.this
        return PlayerCard.IsType(source) or EncounterCard.IsType(source)

    def IsPlayerCardChoiceOption(self) -> bool:
        if not self.IsChoiceOption():
            return False
        message = self.effect.GetBindMessage(Message.WhenPlayerChooseAbility)
        return PlayerCard.IsType(message.by_effect.this)

    def RequiresPayableResourceCost(self) -> bool:
        if self.IsPlayerCardChoiceOption():
            return True
        return self.ability.flags.is_forced_action is True

    def GetSpendCostFunctions(self) -> List['CostFunc.Spend']:
        from game.ability.cost_func import CostFunc
        return [
            cost_func
            for cost_func in self.effect.cost_func.GetAll()
            if isinstance(cost_func, CostFunc.Spend)
        ]

    def HasDynamicPrintedXCost(self) -> bool:
        return bool(
            getattr(self.ability, "play_cost_is_x", False) and
            getattr(self.ability, "cost_fn", None) == None
        )

    def UpdateLegalTargets(self, referential_effect: 'Effect|None'=None) -> bool:
        from game.operate.faces_counter import FacesCounter
        from game.selector.selector import Selector
        effect = self.effect
        ability = self.ability
        allow_partial = self.IsChoiceOption()
        effect.context.allow_partial_resolution = allow_partial

        if isinstance(effect.bind_message, Message.WhenPlayerChooseAbility):
            for_second_target = effect.bind_message.for_second_target
        else:
            for_second_target = False

        if ability.flags.is_statistics:
            return True
        if ability.flags.is_delay_ability:
            return True
        if not ability.selectors:
            return True

        # A stunned/confused character can initiate the matching ability even
        # when that status replacement means no normal target is required.
        if ability.is_label_attack and effect.initiator.GetRoleCharacter().IsStunned() and not for_second_target:
            effect.context.target_range = (0, 0)
            return True
        if ability.is_label_thwart and effect.initiator.GetRoleCharacter().IsConfused() and not for_second_target:
            effect.context.target_range = (0, 0)
            return True

        def get_all_legal_targets(selector: 'Selector', index: int, dont_update_target: bool) -> bool:
            all_legal_targets = list(selector.GetAllLegalTargets(effect, referential_effect))

            # Fix "29033" `divided_evenly`
            if index == 0:
                effect.context.all_legal_targets = all_legal_targets

            target_range = selector.GetTargetRange(
                effect,
                all_legal_targets,
                allow_partial=allow_partial,
            )
            if target_range == None:
                # `failure_reason` is set in `GetTargetRange`
                # self.failure_reason = "target range error"
                return False
            if selector.selector_rule.select_rule == "DifferentType":
                if FacesCounter.GetDifferentTypesCount(all_legal_targets) < target_range[0]:
                    self.failures.Set(effect.initiator, EffectFailure.TypeCountNotEnough)
                    return False
            if selector.selector_rule.select_rule == "MustIncludeTraits" and not allow_partial:
                left_must_include_traits: List['CardFace.TRAITS'] = selector.selector_rule.target_must_include_traits[:]
                for target in all_legal_targets:
                    traits = target.FindHasTrait(*left_must_include_traits)
                    left_must_include_traits = [x for x in left_must_include_traits if x not in traits]
                    if not left_must_include_traits:
                        break
                if left_must_include_traits:
                    self.failures.Set(effect.initiator, EffectFailure.TypeCountNotEnough)
                    return False

            if dont_update_target:
                pass
            elif index == 0:
                effect.context.all_legal_targets = all_legal_targets
                effect.context.target_range = target_range
            else:
                effect.context.all_legal_targets = []
                effect.context.target_range = (0, 0)
            return True

        has_target = False
        is_teamup = False

        for index, selector in enumerate(ability.selectors):
            if selector and \
            (
                selector.condition == None or \
                selector.condition(effect)
            ):
                has_this_target = False
                if not has_target or index == 0 or not selector.is_optional:
                    try:
                        dont_update_target = is_teamup or (not selector.is_optional and index != 0)
                        has_this_target = get_all_legal_targets(selector, index, dont_update_target)
                    except Exception as exc:
                        info = Log.OnCrash(CATEGORY_NAME, exc, effect.GetDisplayName(), None)
                        effect.world.render.ErrorOccurred(info)
                        has_target = False
                        break

                    if not selector.is_optional and not has_this_target:
                        has_target = False
                        break

                    # TeamUp must can select TeamUp characters and its targets
                    if selector.target_text == "TeamUp":
                        is_teamup = True
                        if has_this_target == False:
                            has_target = False
                            break
                        else:
                            if len(ability.selectors) > 1:
                                continue
                has_target |= has_this_target

        return has_target

    def UpdatePayResources(self, player: 'Player') -> bool:
        from game.message import Message
        from game.effect.effect_target_cost import TargetCost
        effect = self.effect
        ability = self.ability

        if player.world.rule.disable_pay:
            effect.context.ignore_resource_cost = True
        else:
            effect.context.ignore_resource_cost = False

        self.effect.this.card.ui.cost.Reset("All")

        self.cost_for_different_target = TargetCost()
        if not effect.context.ignore_resource_cost:
            def process_target(target: 'CardFace|None'):
                if target:
                    targets = [target]
                else:
                    targets = []

                if ability.NeedCost():
                    calc_message = Message.WhenCalculateEffectCost(player, effect, targets)
                    calc_message.Send()
                    base_cost = calc_message.cost
                else:
                    # Keep a zero-sized original-cost component so allocation
                    # indices remain stable while preventing resources from
                    # being assigned away from the actual Spend costs.
                    base_cost = Cost("0", up_to=True)
                component_costs: List[Cost] = []
                combined_cost = base_cost
                spend_costs = [cost_func.cost for cost_func in self.GetSpendCostFunctions()]
                if spend_costs:
                    component_costs = [base_cost] + spend_costs
                    for spend_cost in spend_costs:
                        combined_cost += spend_cost
                self.cost_for_different_target.AddTarget(
                    target,
                    combined_cost,
                    component_costs=component_costs,
                )

                paying_message = Message.CheckPlayerCanPayCost(player, effect, combined_cost, targets)
                paying_message.Send()
                for the_effects in paying_message.can_pay_effects:
                    cost_effect, res, check_effect = the_effects
                    self.cost_for_different_target.AddPayment(target, cost_effect, res, check_effect)
                pass

            if "09039" in [x.paper.card_id for x in effect.context.all_legal_targets]:
                for target in effect.context.all_legal_targets:
                    process_target(target)
            else:
                self.cost_for_different_target.SetNoneTargetOnly()
                process_target(None)

        return True

    ################################################################################
    #
    def CheckBeforeActive(self, player: 'Player') -> bool:
        from game.element.resources import Resources
        effect = self.effect

        def check_target() -> bool:
            if self.ability.selectors != []:
                if not self.ability.selectors[0]:
                    return True
                if not self.ability.selectors[0].AfterSelectTargets(effect, effect.targets, effect.context.target_range):
                    return False
            return True

        def check_pay():
            res_text = ""
            need_cost = ""
            if not self.cost_for_different_target.IsEmpty() and not effect.context.ignore_resource_cost:
                target = effect.targets[0] if effect.targets != [] else None
                payment = self.cost_for_different_target.GetPayment(target)
                if self.HasDynamicPrintedXCost():
                    # Target choice happens before payment in this engine, so
                    # it is the stable declaration of X for the supported
                    # printed-X events. Cost modifiers are then recalculated.
                    effect.context.chosen_cost_x = len(effect.targets)
                    calc_message = Message.WhenCalculateEffectCost(player, effect, effect.targets)
                    calc_message.Send()
                    base_cost = calc_message.cost
                    component_costs = [base_cost]
                    combined_cost = base_cost
                    for spend_cost_func in self.GetSpendCostFunctions():
                        component_costs.append(spend_cost_func.cost)
                        combined_cost += spend_cost_func.cost
                    payment.cost = combined_cost
                    payment.component_costs = component_costs if len(component_costs) > 1 else []
                need_cost = payment.cost
                paid_effects = effect.context.paid_this_res_effects
                effect.context.this_effect_need_cost = need_cost

                effect.context.paid_this_cost = need_cost
                # Validate the chosen resource effects before invoking any of
                # them. Previously an insufficient or canceled allocation was
                # discovered only after the cards had entered the resources
                # area and been discarded.
                selected_resources = self.cost_for_different_target.GetResourcesForEffects(
                    target,
                    paid_effects,
                )
                if not selected_resources.IsMatchCost(need_cost):
                    return False
                if payment.component_costs:
                    allocation = player.AskChooseResourceAllocation(
                        selected_resources,
                        payment.component_costs,
                    )
                    if allocation == None:
                        return False
                    spend_cost_funcs = self.GetSpendCostFunctions()
                    assert len(allocation) == len(spend_cost_funcs) + 1
                    for spend_cost_func, paid_resources in zip(spend_cost_funcs, allocation[1:]):
                        spend_cost_func.SetSimultaneousPayment(paid_resources)

                effect.context.paid_this_resources = player.SpendResource(
                    effect,
                    paid_effects,
                    payment,
                )
                player.res_pool.Reset()
                return effect.context.paid_this_resources.IsMatchCost(need_cost)
            else:
                effect.context.paid_this_resources = Resources("0")
                return True
            self.failures.Set(player, f"pay cost, need {need_cost}, but only have {res_text}")
            return False

        if not check_target():
            self.failures.Set(player, EffectFailure.CheckTarget)
            return False

        # All additional-cost targets and choices are confirmed before any
        # resource card is spent or any exhaust/discard cost changes state.
        if not effect.PrepareSelfCosts():
            self.failures.Set(player, EffectFailure.CheckPay)
            return False

        if not check_pay():
            effect.ClearPreparedSelfCosts()
            self.failures.Set(player, EffectFailure.CheckPay)
            return False

        return True

    def CheckNotOutOfPlay(self) -> bool:
        from game.card.face.card_type import Obligation
        from game.card.face.base import Villain

        this = self.effect.this

        if Obligation.IsType(this):
            if this.card.area.flags.is_processing:
                return False
        if Villain.IsType(this): # Fix "27074"
            if this.IsInPlay() and this.IsThisFaceUp(): # Fix "16080b"
                return True

        if this.card.area.flags.is_status_area and this.IsFaceUp():
            return True

        if self.ability.is_ignore_out_of_play:
            return True

        if self.ability.can_work_also_in_hand:
            if this.IsLikeInHand():
                return True

        # Fix "21032", this must be infront of `IsInPlay`
        if self.ability.can_work_only_in_hand:
            if not this.IsLikeInHand():
                return False
            else:
                return True

        # If a minion with WhenRevealed, it will past this check from here
        if this.IsInPlay(is_same_face=True) and this.IsFaceUp():
            return True

        if this.card.area.flags.is_processing and \
            this.IsFaceUp():
            return True

        if self.ability.is_play:
            return True

        if self.ability.flags.is_when_reveal and \
            this.CanResolveWhenRevealed():
            return True
        if self.ability.flags.is_boost and \
            this.card.area.flags.is_boost_area and \
            this.IsFaceUp():
            return True
        return False

    # def CheckBindFaceIsNotDefeating(self) -> bool:
    #     this = self.this

    #     # if not self.effect.ability.type.is_nonkeyword:
    #     #     return True

    #     face = this.bind_face
    #     if face:
    #         # Fix "27104"
    #         # You can remove threat from Light at the End when you defeat a 
    #         # Sinister Six villain, even if that villain had Taunting Presence attached.
    #         # Fix "16064"
    #         if face.card.state.is_defeating:
    #             return True
    #     return True

    def CheckCondition(self, message: 'Message2', asked_player: 'Player|None', *, initiating_play: bool=False) -> bool:
        this = self.effect.this

        # Player card abilities cannot resolve during game setup,
        # unless prefaced by a "Setup" timing trigger.
        # Fix "01019b", "50067a", "20001b"
        if not self.effect.world.is_game_started and \
            not isinstance(message, Message.WhenPlayerChooseAbility) and \
            not self.effect.is_forced and \
            not self.ability.flags.is_setup and \
            PlayerCard.IsType(this):
            return False

        # Fix there are more than 3 allies and defeat "50081"
        # if this.card.state.is_defeating:
        #     return False

        if not self.CheckNotOutOfPlay():
            self.failures.Set(asked_player, EffectFailure.OutOfPlay)
            return False

        # Fix "27153", "39071"
        if this.card.area.flags.is_revealing and \
            self.effect.ability.flags.is_nonkeyword and \
            not self.effect.ability.IsFunction("AttachToWhenEnterPlay") and \
            not self.effect.ability.IsFunction("CheckAllyLimit"):
            return False

        # if not self.CheckBindFaceIsNotDefeating():
        #     self.failures.Set(asked_player, EffectFailure.BindFaceIsDefeating)
        #     return False

        if self.ability.is_play:
            if asked_player:
                if this.card.area == asked_player.hand_cards:
                    pass
                elif this.GetOwner() != asked_player:
                    self.failures.SetText(asked_player, f"{asked_player} doesn't have this card")
                    return False

        if message.send_resolve_message:
            if not self.ability.flags.is_statistics:
                check_message = Message.CheckEffectCondition(self.effect, this)
                check_message.Send()
                if not check_message.effect_valid:
                    self.failures.SetText(asked_player, str([x.this for x in check_message.cause_by]))
                    return False

        for condition in self.ability.conditions:
            # During step 2 of play initiation the card is already faceup on
            # the table. The generated preflight-only hand check must not make
            # the declared play illegal merely because step 1 succeeded.
            if initiating_play and condition is self.ability.play_location_condition:
                continue
            if not self.effect.is_forced and self.effect.initiator != asked_player:
                self.failures.SetText(asked_player, f"asking {asked_player}, but initiator is {self.effect.initiator}")
                return False
            try:
                if not condition(self.effect, message):
                    self.failures.SetText(asked_player, GetFuncName(condition))
                    return False
            except Exception as exc:
                info = Log.OnCrash(CATEGORY_NAME, exc, self.effect.GetDisplayName(), condition)
                self.effect.world.render.ErrorOccurred(info)
                return False

        if isinstance(message, Message.WhenPlayerChooseAbility):
            by_effect = message.by_effect
        else:
            by_effect = self.effect

        if not self.UpdateLegalTargets(by_effect):
            self.failures.Set(asked_player, EffectFailure.UpdateLegalTargets)
            return False

        if not self.HasCostTargets():
            self.failures.Set(asked_player, EffectFailure.NoCostTarget)
            return False

        if self.ability.NeedCost() or self.GetSpendCostFunctions():
            if not asked_player:
                self.failures.Set(asked_player, EffectFailure.HasCostButNoAskPlayer)
                assert False, f"{self=}"
            self.UpdatePayResources(asked_player)
            if self.RequiresPayableResourceCost() and \
                not self.effect.context.ignore_resource_cost and \
                not self.cost_for_different_target.HasPayableTarget():
                self.failures.Set(asked_player, EffectFailure.CheckPay)
                return False

        if self.ability.is_label_defense:
            # from game.message.message_type import AttackerMessageInternal
            if isinstance(message, AttackerMessageInternal):
                if message.has_resolves_defense_labeled_ability != None and \
                    message.has_resolves_defense_labeled_ability != asked_player:
                    self.failures.Set(asked_player, EffectFailure.AlreadyResolvesDefense)
                    return False

        self.failures.Set(asked_player, EffectFailure.OK)
        return True

    def CheckPlayInitiation(self, message: 'Message2', player: 'Player') -> bool:
        """Run the normative RR 1.8 step-2/3 check after table placement."""
        effect = self.effect
        assert self.ability.is_play

        if effect.context.play_initiation_checked:
            return effect.context.play_initiation_allowed

        effect.context.play_initiation_checked = True
        if not effect.this.card.area.flags.is_processing:
            effect.context.play_initiation_allowed = False
            return False
        effect.context.ask_player = player
        allowed = self.CheckCondition(
            message,
            player,
            initiating_play=True,
        )
        effect.context.play_initiation_allowed = allowed
        return allowed
