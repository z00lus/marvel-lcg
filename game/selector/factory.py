from typing import TypeAlias
from core import *
from game.card.face import *
from game.effect import *
from game.selector import *
from game.message import *
from game.player import *
from game.world.game_area import *
from game.deck import *

from game.selector.selector_rule import SelectorRule
from game.selector.selector_target import SelectorTarget
from game.selector.selector_where import SelectorWhere
from game.selector.selector_range import SelectorRange

class SELECT:
    RULE                : TypeAlias = 'SelectorRule.RULE_BASE'
    REPEAT_RULE         : TypeAlias = 'SelectorRule.REPEAT_RULE'
    RANGE_TYPE          : TypeAlias = 'SelectorRange.RANGE_TYPE'
    WHERE               : TypeAlias = 'SelectorWhere.WHERE'
    TARGET_TYPE_HELPER  : TypeAlias = 'SelectorTarget.TARGET_TYPE_HELPER'
    TARGET_TYPE         : TypeAlias = 'SelectorTarget.TARGET_TYPE'

    HELPER_TYPE: TypeAlias = 'Callable[[Effect], Sequence[CardFace]]|Literal["YourPlayerDeckTop", "EncounterDeckTop","RandomHandCard",]|SELECT.TARGET_TYPE|SELECT.TARGET_TYPE_HELPER|CardFinderHelper.FINDER_TARGET'

# Factory
class Select:

    @staticmethod
    def GetYouSafe(effect: 'Effect') -> 'Player|None':
        if not effect.this.IsInPlay():
            return None
        return Select.GetYou(effect)

    @staticmethod
    def GetYou(effect: 'Effect') -> 'Player':
        from game.player import Player
        from game.card.face.card_type import Obligation
        from game.card.face.card_type import Minion
        from game.card.face.base.scheme import Scheme2
        from game.message import TriggerNonePlayerMessage
        from game.operate.worlds import Worlds

        if effect.context.ask_player:
            return effect.context.ask_player
        elif Obligation.IsType(effect.this):
            return effect.this.GetGaveToPlayer()
        elif Minion.IsType(effect.this):
            return effect.this.GetEngagedPlayer()
        elif Scheme2.IsType(effect.this):
            return Worlds.GetCurrentPlayer(effect)
        else:
            if isinstance(effect.initiator, Player):
                return effect.GetInitiator()
            else:
                message = effect.bind_message
                
                if isinstance(message, TriggerNonePlayerMessage) and message.to_player:
                    return message.to_player
                # from game.event.sender import TriggerUnitMessage
                # if isinstance(message, TriggerUnitMessage):
                #     return message.trigger.GetController()
                assert False, f"{effect=} {message=}"

    ################################################################################
    #
    @staticmethod
    def From(target: 'SELECT.HELPER_TYPE|CardFinder|None'=None,
            *,
            faces: Sequence['CardFace']|None=None,
            from_where: List['SELECT.WHERE']=["Default"],

            ################################################################################
            # Filter
            finder: 'CardFinder|None'=None,
            affects_target_if: Sequence[Callable[['Effect', 'CardFace'], bool]]=(),
            another: bool|None=None, # Not `effect.this`
            corresponding: Literal["ActiveVillain"]|None=None,
            exclude: List['CardFace']|Literal["Trigger", "Attacker", "This", "Targets"]=[],
            most_printed_res: bool=False,
            most_remaining_hp: bool=False,
            fewest_remaining_hp: bool=False,
            lowest_atk: bool=False,
            highest_atk: bool=False,
            highest_thw: bool=False,
            highest_sch: bool=False,
            lowest_sch: bool=False,
            highest_printed_hp: bool=False,
            highest_printed_atk: bool=False,
            lowest_printed_atk: bool=False,
            lowest_order: bool=False,
            highest_order: bool=False,
            most_traits: bool=False,
            least_threat: bool=False,
            most_threat: bool=False,
            highest_cost: bool=False,
            lowest_cost: bool=False,
            share_trait_with_your_hero: bool=False,
            share_trait_with_your_identity: bool=False,

            ################################################################################
            # Select rule
            random: bool=False,
            combined_resource_cost: Tuple[int, int]|None=None,
            combined_printed_cost: Tuple[int, int]|None=None,
            combined_resource_icons: Tuple[int, int]|None=None,

            range: 'SELECT.RANGE_TYPE'=(1,1),

            select_rule: 'SELECT.RULE'="",
            repeat_rules: List['SELECT.REPEAT_RULE']|'SELECT.REPEAT_RULE'=[],

            # Process rule
            by_search: bool=False, # will peek
            not_move: bool=False,
            not_shuffle: bool=False,

            check_again_fn: Callable[['Effect', Sequence['CardFace']], bool]|None=None,
        ) -> 'Selector':
        from game.selector.selector_target import SelectorTarget
        from game.selector.selector_rule import SelectorRule
        from game.selector.selector_filter import SelectorFilter
        from game.selector.selector_end import SelectorEnd
        from game.selector.selector import Selector
        from game.card.card_finder import CardFinder, CardFinderHelper

        from game.card.face.card_type import Hero
        from game.card.face.card_type import Ally
        from game.card.face.card_type import Minion
        from game.card.face.base import Villain
        from game.card.face.card_type import Support
        from game.card.face.card_type import Upgrade
        from game.card.face import MainScheme, Villain, Identity

        finder3: 'CardFinder|None' = None
        target_type = None

        from_where2 = from_where[:]
        get_targets_fn = None

        if isinstance(target, Selector):
            return target
        elif target == None or isinstance(target, CardFinder):
            finder3 = target
        elif isinstance(target, Callable):
            get_targets_fn = target
        elif SelectorTarget.IsHelpType(target):
            target_type = target
        elif CardFinderHelper.IsFinderTarget(target):
            # finder3 = CardFinderHelper.From(target)
            target_type = target
        elif target == "MainScheme":
            finder3 = CardFinder(card_type=MainScheme)
        elif target == "Villain":
            finder3 = CardFinder(card_type=Villain)
        elif target == "Identity":
            finder3 = CardFinder(card_type=Identity)
        elif target == "YourIdentity":
            def check(effect: 'Effect', face: 'CardFace'):
                return Select.GetYou(effect).GetIdentity() == face
            finder3 = CardFinder(card_type=Identity, check_effect_fn=check)
        elif target == "Hero|Ally":
            finder3 = CardFinder(card_type=Hero|Ally)
        elif target == "Hero|Villain":
            finder3 = CardFinder(card_type=Hero|Villain)
        elif target == "Ally|Minion":
            finder3 = CardFinder(card_type=Ally|Minion)
        elif target == "Upgrade|Support":
            finder3 = CardFinder(card_type=Upgrade|Support)
        elif target == "YourSuitFormUpgrade":
            def check(effect: 'Effect', face: 'CardFace'):
                return Select.GetYou(effect) == face.GetControlBy()
            finder3 = CardFinder(card_type=Upgrade, form="Suit", check_effect_fn=check)
        elif target == "YourHandCards":
            from_where2.append("YourHandCards")
        elif target == "RandomHandCard":
            random = True
            from_where2.append("YourHandCards")
        elif target == "YourPlayerDeckTop":
            from_where2.append("YourPlayerDeckTop")
        elif target == "EncounterDeckTop":
            from_where2.append("EncounterDeckTop")
        elif target == "YourHeroTough":
            def check(effect: 'Effect', face: 'CardFace'):
                identity = Select.GetYou(effect).GetIdentity()
                return Hero.IsType(identity) and identity == face.GetBindFace()
            finder3 = CardFinder(name="Tough", check_effect_fn=check)
        else:
            target_type = target

        card_type = None
        if finder3:
            card_type = finder3.card_type
        if card_type == None and finder:
            card_type = finder.card_type

        selector_target = SelectorTarget(
            target_type,
            faces,
            get_targets_fn,
            from_where2,
        )

        forced_range_rule =  selector_target.GetForcedRangeRule()
        select_rule_internal = select_rule
        if forced_range_rule:
            forced_range, forced_rule = forced_range_rule
            if forced_range:
                range = forced_range
            if forced_rule:
                select_rule_internal = forced_rule

        ################################################################################
        # SelectorFilter
        if finder3:
            card_finder = finder3 & finder
        elif finder:
            card_finder = finder
        else:
            card_finder = CardFinder()

        selector_filter = SelectorFilter(
            card_finder,
            affects_target_if=affects_target_if,
            # bind_to=bind_to,
            another=another,
            corresponding=corresponding,
            # check_fn=check_fn,
            exclude=exclude,
            most_printed_res=most_printed_res,
            most_remaining_hp=most_remaining_hp,
            fewest_remaining_hp=fewest_remaining_hp,
            lowest_atk=lowest_atk,
            highest_atk=highest_atk,
            highest_thw=highest_thw,
            highest_sch=highest_sch,
            lowest_sch=lowest_sch,
            highest_printed_hp=highest_printed_hp,
            highest_printed_atk=highest_printed_atk,
            lowest_printed_atk=lowest_printed_atk,
            lowest_order=lowest_order,
            highest_order=highest_order,
            most_traits=most_traits,
            least_threat=least_threat,
            most_threat=most_threat,
            share_trait_with_your_hero=share_trait_with_your_hero,
            share_trait_with_your_identity=share_trait_with_your_identity,
            highest_cost=highest_cost,
            lowest_cost=lowest_cost,
        )

        ################################################################################
        # SelectorRule
        if not isinstance(repeat_rules, list):
            repeat_rules = [repeat_rules]

        selector_rule = SelectorRule(
            random=random,
            select_rule=select_rule_internal,
            repeat_rules=repeat_rules,
            combined_resource_cost=combined_resource_cost,
            combined_printed_cost=combined_printed_cost,
            combined_resource_icons=combined_resource_icons,
            top_bottom_most=len(from_where2) == 1 and (from_where2[0].endswith("Topmost") or from_where2[0].endswith("Bottommost")),
            target_must_include_traits=selector_filter.target_must_include_traits
        )

        selector_range = SelectorRange(
            range,
            selector_rule,
        )

        ################################################################################
        # SelectorEnd
        for deck in from_where2:
            if deck.endswith("DeckTop"):
                not_move=True
                not_shuffle=True

        selector_end = SelectorEnd(
            peek=by_search,
            not_move=not_move,
            not_shuffle=not_shuffle
        )

        ################################################################################
        #
        return Selector(
            selector_target,
            selector_rule,
            selector_filter,
            selector_range,
            selector_end,
            check_again_fn=check_again_fn,
            target_text=Cast(Any, target) if isinstance(target, str) else None
        )

    @staticmethod
    def Alliance(traits: List["CardFace.TRAITS"], card_type: 'Type[Ally|Friend]|None'=None) -> 'Selector':
        from game.card.face.base import Friend
        from game.card.card_finder import CardFinder
        if card_type == None:
            card_type = Friend
        selector = Select.From(
            CardFinder(traits=traits, card_type=card_type),
            range=(2, 2),
            select_rule="MustIncludeTraits"
        )
        return selector
