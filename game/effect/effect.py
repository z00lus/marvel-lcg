from typing import Final
from core import *
from game.card.face import *
from game.effect import *
from game.message import *
from game.player import *
from game.element.resources import Resources
from game.render.descriptor.effect import EffectDescriptor
from game.object import Object
from engine.log import Log
from engine.profile import Coverage
from game.message.message_type import HasPreEventMessage, HasEndEventMessage
from game.world import *
from game.effect.effect_failure import EffectFailure
from game.effect.effect_invoke import EffectInvoker

Unused(EffectFailure)

CATEGORY_NAME = "EFFECT"

class Effect(Object):

    def __init__(self, face: 'CardFace', ability: 'Ability', *, is_temp: bool=False, is_local: bool=False, world: 'World') -> None:
        from game.card.face.card_type import Event
        from game.message import Message
        from game.effect.effect_checker import EffectChecker
        from game.effect.effect_context import EffectContext
        from game.effect.effect_cost_func import EffectCostFunction

        self.this: 'CardFace' = face
        ability.Initialize(self.this)

        self.ability: Final = ability
        self.priority: Final = ability.flags.GetPriority(world.rule)
        self.delay_ability: 'Ability|None' = None

        self.checker = EffectChecker(self)
        self.failures = self.checker.failures
        self.cost_func = EffectCostFunction(self)
        self.context = EffectContext(self)

        if Coverage.is_enable:
            Coverage.RegisterFunction(self.ability.operation)

        # disposable
        self.is_unregister_after_exec = False
        self.is_temp: Final = is_temp or self.ability.flags.is_temp
        self.is_nonkeyword: Final = self.ability.flags.is_nonkeyword
        self.is_unregister = False
        self.is_local = is_local

        # Debug Check
        if not self.is_forced:
            if not Event.IsType(self.this):
                assert self.ability.when != Message.WhenCardRevealed, f"{self.this=} {self.ability=}"

        if ability.is_choose:
            super().__init__('choose_effect', world)
        elif self.is_forced:
            super().__init__('forced_effect', world)
        elif ability.is_paying:
            super().__init__('paying_effect', world)
        else:
            super().__init__('effect', world)

    @property
    def is_rule(self) -> bool:
        return self.ability.flags.is_rule

    @property
    def initiator(self) -> 'User':
        return self.context.initiator

    @property
    def bind_message(self) -> 'Message2|None':
        return self.context.bind_message

    @property
    def targets(self) -> List['CardFace']:
        return self.context.targets_internal

    @property
    def targets2(self) -> List['CardFace']:
        return self.context.GetTargetsInternal(1)

    @property
    def targets3(self) -> List['CardFace']:
        return self.context.GetTargetsInternal(2)

    def IsPaidForWithCardType(self, card_type: Type['CardFace']) -> bool:
        for effect in self.context.paid_this_res_effects:
            if card_type.IsType(effect.this):
                return True
        return False

    @property
    def is_forced(self) -> bool:
        return self.ability.flags.is_forced

    @property
    def is_action(self) -> bool:
        return self.ability.flags.is_action

    @property
    def must_choose(self) -> bool:
        return self.context.is_must_choose or self.ability.default_choose

    def SetMustChoose(self):
        self.context.is_must_choose = True

    def __repr__(self) -> str:
        before = ""
        if self.is_local:
            before += "^" # this (local)
        if self.is_forced:
            before += "!"
        if self.ability.flags.is_delay_ability:
            before += "_" # delay
        # if self.ability.type.is_discard_pay or self.ability.type.is_resource:
        #     before = "+"
        auto_unregister = "Auto " if self.is_unregister_after_exec else ""
        return f'({before}{self.object_id}) {self.this} {auto_unregister}{self.ability}'

    def GetBindMessage(self, event: Type[TMP]) -> 'TMP':
        assert self.bind_message != None
        return self.bind_message.CastTo(event)

    def GetReplayText(self) -> str:
        # ability_name = self.ability.name if self.ability.name else self.ability.sub_types[0] if self.ability.sub_types else ''
        ability_name = self.GetDisplayName(remove_space=True)
        assert ability_name != ""
        return f"e{self.object_id} {ability_name} " + self.this.GetReplayText()

    ################################################################################
    #
    def ClearPreparedSelfCosts(self) -> None:
        for cost_func in self.cost_func.GetAll():
            cost_func.ClearPreparedCost()
        self.context.self_costs_prepared = False

    def PrepareSelfCosts(self) -> bool:
        """Confirm every additional-cost choice before paying any of them."""
        if self.context.self_costs_prepared:
            return True

        for cost_func in self.cost_func.GetAll():
            try:
                if not cost_func.PrepareCost(self, self.initiator):
                    self.ClearPreparedSelfCosts()
                    return False
            except Exception as exc:
                info = Log.OnCrash(CATEGORY_NAME, exc, self.GetDisplayName(), cost_func.call_fn)
                self.world.render.ErrorOccurred(info)
                self.ClearPreparedSelfCosts()
                return False

        self.context.self_costs_prepared = True
        return True

    def ValidatePreparedSelfCosts(self) -> bool:
        """Validate the complete prepared cost set before its first commit."""
        reservations: Set[Tuple[str, int]] = set()
        consumptions: Dict[Tuple[str, int, str], Tuple[int, int]] = {}
        for cost_func in self.cost_func.GetAll():
            try:
                valid = cost_func.ValidatePreparedCost(self)
            except Exception as exc:
                info = Log.OnCrash(
                    CATEGORY_NAME,
                    exc,
                    self.GetDisplayName(),
                    cost_func.call_fn,
                )
                self.world.render.ErrorOccurred(info)
                return False
            if not valid:
                return False
            for kind, target in cost_func.GetPreparedReservations():
                reservation = (kind, id(target))
                if reservation in reservations:
                    return False
                reservations.add(reservation)
            for kind, target, name, requested, available in cost_func.GetPreparedConsumptions():
                key = (kind, id(target), name)
                total, previous_available = consumptions.get(key, (0, available))
                if previous_available != available:
                    return False
                total += requested
                if total > available:
                    return False
                consumptions[key] = (total, available)
        return True

    def ProcessSelfCost(self) -> bool:
        if not self.PrepareSelfCosts():
            return False

        # Revalidate every choice as one set before committing the first
        # mutation. This catches stale targets and mutually exclusive costs
        # (such as exhausting the same card twice) without partial payment.
        if not self.ValidatePreparedSelfCosts():
            self.ClearPreparedSelfCosts()
            return False

        for cost_func in self.cost_func.GetAll():
            try:
                if not cost_func.CommitCost(self, self.initiator):
                    self.ClearPreparedSelfCosts()
                    return False
            except Exception as exc:
                info = Log.OnCrash(CATEGORY_NAME, exc, self.GetDisplayName(), cost_func.call_fn)
                self.world.render.ErrorOccurred(info)
                self.ClearPreparedSelfCosts()
                return False
        self.context.self_costs_prepared = False
        return True


    def ResolveToPlayer(self, to_player: 'Player', by_effect: 'Effect', ref_message: 'Message2|None') -> bool:
        result = EffectInvoker.ResolveSelfInternal(self, None, to_player, by_effect, ref_message, skip_cost=True)
        return result

    def ResolveSelf(self, message: 'Message2|None', by_effect: 'Effect', *, to_player: 'Player|None'=None, skip_cost: bool=False) -> bool:
        result = EffectInvoker.ResolveSelfInternal(self, message, to_player, by_effect, skip_cost=skip_cost)
        return result

    def SetHasSpellInPhase(self) -> None:
        world = self.world

        if self.ability.flags.is_rule or self.ability.flags.is_statistics:
            return

        if not world.rule.disable_limit_once:
            if  self.ability.flags.is_interrupt or \
                self.ability.flags.is_response or \
                self.ability.flags.is_resource or \
                self.ability.flags.is_when_completed or \
                self.ability.flags.is_when_reveal or \
                self.ability.flags.is_when_defeated or \
                self.ability.flags.is_setup or \
                self.ability.flags.is_boost or \
                self.ability.flags.is_special or \
                self.ability.flags.is_action or \
                self.ability.flags.is_nonkeyword:

                if isinstance(self.bind_message, TriggerNonePlayerMessage) and self.bind_message.to_player != None:
                    player = self.bind_message.GetToPlayer()
                    effect = self
                    world.stat.RecordEffectWithPlayer(effect, player)

                if isinstance(self.bind_message, Message.WhenPlayerPayingResources):
                    effect = self.bind_message.cost_check_effect
                    world.stat.RecordEffect(effect)

                world.stat.RecordEffect(self)

                self.GetBindMessage(self.ability.when).once_per_event_effects.append(self)

    def UnRegisterSelf(self):
        assert self.is_temp or self.ability.flags.is_statistics, f"{self=}"
        if self in self.this.effect.local_effects:
            self.is_unregister = True
            self.this.effect.local_effects.remove(self)
        elif self in self.this.effect.given_effects:
            self.is_unregister = True
            self.this.effect.given_effects.remove(self)
        else:
            self.this.effect.global_effects.remove(self)
            self.world.event_manager.UnRegisterEffect(self)

    def SetDestroyedAfter(self, unregister_after_exec: bool,
                        until_turn_end: bool=False,
                        until_next_turn_end: bool=False,
                        until_phase_end: bool=False,
                        until_round_end: bool=False,
                        until_this_leave_play: bool=False,
                        until_after_event: 'HasEndEventMessage|Message.WhenUnitWouldAttack|Message.WhenUnitWouldThwart|Message.WhenUnitWouldScheme|Message.WhenUnitWouldDefend|None'=None,
                        until_after_resolve_effect: 'Effect|None'=None,
                        ) -> 'Effect':
        assert self.is_temp, f"{self.ability.flags=}"
        from game.ability.factory import AbilityFactory
        from game.ability import AbilityType
        from game.operate.effects import Effects
        from game.ability import Ability

        self.is_unregister_after_exec = unregister_after_exec
        temp_effects: List['Effect'] = []

        def try_unregister(effect: 'Effect'):
            if not effect.is_unregister:
                effect.UnRegisterSelf()
            Effects.UnRegister([x for x in temp_effects if not x.is_unregister])

        if until_turn_end:
            assert until_phase_end == False
            assert until_round_end == False
            temp_effects += self.this.effect.RegisterTemp(
                AbilityFactory.WhenPlayerTurnEnd(
                    AbilityType.Temp0,
                    "This",
                    lambda effect, message:
                        try_unregister(self),
                ),
                unregister_after_exec=True,
            )

        if until_next_turn_end:
            temp_effects += self.this.effect.RegisterTemp(
                AbilityFactory.WhenPlayerTurnEnd(
                    AbilityType.Temp0,
                    "This",
                    lambda effect, message:
                        try_unregister(self),
                    round_id=self.world.round_id+1,
                ),
                unregister_after_exec=True,
            )

        if until_phase_end:
            assert until_turn_end == False
            assert until_round_end == False
            temp_effects += self.this.effect.RegisterTemp(
                AbilityFactory.AfterPhaseEnd(
                    AbilityType.Temp0,
                    None,
                    lambda effect, message:
                        try_unregister(self),
                ),
                unregister_after_exec=True,
            )

        if until_round_end:
            assert until_turn_end == False
            assert until_phase_end == False
            temp_effects += self.this.effect.RegisterTemp(
                AbilityFactory.AfterRoundEnd(
                    AbilityType.Temp0,
                    lambda effect, message:
                        try_unregister(self),
                ),
                unregister_after_exec=True,
            )

        if until_this_leave_play:
            temp_effects += self.this.effect.RegisterTemp(
                AbilityFactory.AfterCardLeavePlay(
                    AbilityType.Temp0,
                    self.this,
                    lambda effect, message:
                        try_unregister(self),
                ),
                unregister_after_exec=True,
            )

        if isinstance(until_after_event, Message.WhenUnitWouldDefend):
            temp_effects += self.this.effect.RegisterTemp(
                AbilityFactory.AfterUnitAttackEnd(
                    AbilityType.Temp0,
                    None,
                    lambda effect, message:
                        try_unregister(self),
                    conditions=[
                        lambda effect, message:
                            until_after_event.would_atk_message in message.would_atk_messages,
                    ]
                ),
                unregister_after_exec=True,
            )
        elif isinstance(until_after_event, Message.WhenUnitWouldAttackUnit):
            temp_effects += self.this.effect.RegisterTemp(
                AbilityFactory.AfterUnitAttackEnd(
                    AbilityType.Temp0,
                    None,
                    lambda effect, message:
                        try_unregister(self),
                    conditions=[
                        lambda effect, message:
                            until_after_event.would_atk_message in message.would_atk_messages,
                    ]
                ),
                unregister_after_exec=True,
            )
        elif isinstance(until_after_event, Message.WhenUnitWouldAttack):
            temp_effects += self.this.effect.RegisterTemp(
                AbilityFactory.AfterUnitAttackEnd(
                    AbilityType.Temp0,
                    None,
                    lambda effect, message:
                        try_unregister(self),
                    conditions=[
                        lambda effect, message:
                            until_after_event in message.would_atk_messages,
                    ]
                ),
                unregister_after_exec=True,
            )
        elif isinstance(until_after_event, Message.WhenUnitWouldThwart):
            temp_effects += self.this.effect.RegisterTemp(
                AbilityFactory.AfterUnitThwartEnd(
                    AbilityType.Temp0,
                    None,
                    lambda effect, message:
                        try_unregister(self),
                    conditions=[
                        lambda effect, message:
                            until_after_event in message.would_thw_messages,
                    ]
                ),
                unregister_after_exec=True,
            )
        elif isinstance(until_after_event, Message.WhenUnitWouldScheme):
            temp_effects += self.this.effect.RegisterTemp(
                AbilityFactory.AfterUnitSchemeEnd(
                    AbilityType.Temp0,
                    None,
                    lambda effect, message:
                        try_unregister(self),
                    conditions=[
                        lambda effect, message:
                            until_after_event in message.would_sch_messages,
                    ]
                ),
                unregister_after_exec=True,
            )
        elif isinstance(until_after_event, Message.WhenCardWouldLeavePlay):
            temp_effects += self.this.effect.RegisterTemp(
                AbilityFactory.AfterCardLeavePlay(
                    AbilityType.Temp2,
                    None,
                    lambda effect, message:
                        try_unregister(self),
                    conditions=[
                        lambda effect, message:
                            until_after_event == message.would_leave_play_message,
                    ]
                ),
                unregister_after_exec=True,
            )
        elif until_after_event != None:
            temp_effects += self.this.effect.RegisterTemp(
                Ability(
                    AbilityType.Temp2,
                    until_after_event.end_event,
                    [
                        lambda effect, message:
                            until_after_event == message.CastTo(HasPreEventMessage).pre_message,
                    ],
                    lambda effect, message:
                        try_unregister(self),
                ),
                unregister_after_exec=True,
            )

        if isinstance(until_after_event, CanBeInstead):
            temp_effects += self.this.effect.RegisterTemp(
                Ability(
                    AbilityType.Temp2,
                    Message.WhenMessageBeInstead,
                    [
                        lambda effect, message:
                            until_after_event == message.message,
                    ],
                    lambda effect, message:
                        try_unregister(self),
                ),
                unregister_after_exec=True
            )

        if until_after_resolve_effect:
            from cards.pack import RunAt
            def action():
                try_unregister(self)
            RunAt.AfterResolveEffect(until_after_resolve_effect, until_after_resolve_effect, action)

        return self

    def Copy(self) -> 'Effect':
        from copy import copy
        return copy(self)

    def IsName(self, name: str) -> bool:
        return self.ability.name == name

    def IsType(self, type: AbilityType) -> bool:
        return self.ability.flags.IsType(type)

    def GetInitiator(self) -> 'Player':
        from game.player import Player
        assert isinstance(self.initiator, Player), f"{self.initiator=}"
        return self.initiator

    def IsPlayerInitiator(self) -> 'bool':
        # if self.initiator == None:
        #     return False
        return self.initiator.IsPlayer()

    def GetDisplayName(self, *, remove_space: bool=False) -> str:
        from game.card.face.card_type import Upgrade
        from game.card.face.card_type import Event
        from game.card.face.card_type import Ally
        from game.card.face.card_type import Identity
        def get_name() -> str:
            if Identity.IsType(self.this) or Ally.IsType(self.this):
                if self.ability.IsFunction("ATK"):
                    return "Attack"
                if self.ability.IsFunction("DEF"):
                    return "Defense"
                if self.ability.IsFunction("THW"):
                    return "Thwart"
                if self.ability.IsFunction("REC"):
                    return "Recover"
                if self.ability.IsFunction("Change Form") and not self.ability.name:
                    return "Change Form"
                if self.ability.IsFunction("Ask"):
                    return "Ask"

            if self.ability.flags.is_temp:
                return "Temp"
            if self.ability.name:
                return self.ability.name
            if self.ability.flags.is_resource:
                return "Resource"
            if self.ability.is_play:
                return "Play"
            if self.ability.flags.is_choose_ability:
                return "Choose"
            if self.ability.flags.ui_display_name:
                return self.ability.flags.ability_type.value
            if self.this.card.IsInHand():
                return ""
            if Event.IsType(self.this):
                return ""
            if not Upgrade.IsType(self.this):
                if self.ability.labels:
                    return " ".join(self.ability.labels)
            # return str(self.ability.type)
            return ""
        name = get_name()

        # Fix replay for "10029"
        if self.ability.flags.is_action:
            effects = self.this.effect.Find(type=self.ability.type)
            index = effects.index(self)
            if index != 0:
                name = f"{name}_{index}"

        if remove_space:
            return name.replace(' ', '_')
        else:
            return name

    def IsIgnoreKeyword(self, keyword: 'CardFace.ABILITY_IGNORE_KEY', effect: 'Effect') -> bool:
        if effect.is_rule:
            return True

        if effect.world.rule.encounter_cards_ignore_crisis and keyword == "Crisis":
            if effect.this.GetControlByOrOwner().IsScenario():
                return True
        if self.ability.ignore.keyword[keyword](effect):
            return True
        if keyword == "Guard" and not effect.ability.is_like_attack:
            return False
        if keyword == "Patrol" and not effect.ability.is_like_thwart:
            return False
        message = Message.CheckIfEffectIsIgnoreKeyWord(self, keyword)
        message.Send()
        if message.is_ignore_this_keyword:
            return True
        return False

    ################################################################################
    #
    def GetPaidResources(self, ask_specify_green: bool=False) -> 'Resources':
        res = self.context.paid_this_resources.Copy()
        if ask_specify_green:
            initiator = self.GetInitiator()
            res = initiator.AskSpecifyResources(res)
        return res

    def GetCostX(self) -> 'int':
        if self.ability.play_cost_is_x and \
            self.ability.cost_fn == None and \
            self.context.chosen_cost_x != None:
            return self.context.chosen_cost_x
        return self.context.paid_this_resources.val - self.context.paid_this_cost.true_val

    ################################################################################
    #
    def Render(self, by_effect: 'Effect|None', bind_player_id: int) -> 'EffectDescriptor':
        def get_pay_info(effect: 'Effect') -> Dict[int, 'EffectDescriptor.Payment']:
            def get_cost_str_rule(effect: 'Effect', target: 'CardFace|None') -> Tuple[str, List[str]]:
                if effect.failures.GetText(bind_player_id):
                    # this should not happen
                    return ("0", [])
                if effect.context.ignore_resource_cost:
                    return ("*", [])
                if effect.checker.cost_for_different_target.HasTarget(target):
                    cost = effect.checker.cost_for_different_target.GetCost(target)
                    if cost.rule.or_res != None:
                        return ("1", [])
                    else:
                        return (cost.text_legacy, cost.GetRuleText())
                # if target in effect.for_select_target_dict:
                #     # return effect.this_effect_cost.text_legacy
                #     return effect.for_select_target_dict[target].cost.text_legacy
                return ("", [])

            payinfo_dict: Dict[int, EffectDescriptor.Payment] = {}
            for target in effect.checker.cost_for_different_target.target_cost:
                if target == None:
                    target_id = 0
                else:
                    target_id = target.card.object_id

                cost_text, cost_rule = get_cost_str_rule(effect, target)
                payinfo_dict[target_id] = EffectDescriptor.Payment(
                    cost=cost_text,
                    payment=[],
                    rule=cost_rule
                )
                if effect.context.ignore_resource_cost:
                    continue
                for effect_res in effect.checker.cost_for_different_target.target_cost[target].payments:
                    for pay_effect in effect_res:
                        payinfo_dict[target_id].payment.append({pay_effect.object_id: effect_res[pay_effect]})
            return payinfo_dict

        the_effect = self
        if by_effect:
            the_effect = by_effect

        if by_effect != None and self.ability.name == "":
            name = by_effect.GetDisplayName(remove_space=True)
        else:
            name = self.GetDisplayName(remove_space=True)

        bind_id = the_effect.this.card.object_id

        selector = self.ability.selectors[0] if self.ability.selectors else None
        if selector:
            select_rule, select_rule_param = selector.selector_rule.GetRuleAndParam()
            if self.context.allow_partial_resolution:
                target_must_include_traits = []
            else:
                target_must_include_traits = selector.selector_rule.target_must_include_traits
        else:
            select_rule = ""
            select_rule_param = (0, 0)
            target_must_include_traits = []

        if selector:
            is_search = selector.is_search
        else:
            is_search = False

        # Fix "07042"
        failure_reason = self.failures.GetText(bind_player_id)
        if self.failures.IsNoProcess(bind_player_id):
            failure_reason = ""

        return EffectDescriptor(
            id=self.object_id,
            name=name,
            bind_id=bind_id,
            bind_player_id=bind_player_id,
            all_legal_targets=[face.card.object_id for face in self.context.all_legal_targets],
            target_num_range=list(self.context.target_range),
            target_payment=get_pay_info(self),
            select_rule=select_rule,
            select_rule_param=select_rule_param,
            target_must_include_traits=[f"t_{x}" for x in target_must_include_traits],
            failure_reason=failure_reason,
            is_search=is_search
        )
