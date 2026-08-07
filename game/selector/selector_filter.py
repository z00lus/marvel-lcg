from core import *
from game.card.face import *
from game.effect import *
from game.message import *

CATEGORY_NAME = "SELECTOR"

class FilterArgs(TypedDict, total=False):
    most_traits: bool
    highest_cost: bool
    lowest_cost: bool
    most_printed_res: bool
    engaged_with_fewest_minions: bool
    most_remaining_hp: bool
    fewest_remaining_hp: bool
    highest_printed_hp: bool
    highest_atk: bool
    lowest_atk: bool
    highest_printed_atk: bool
    lowest_printed_atk: bool
    highest_thw: bool
    lowest_thw: bool
    highest_sch: bool
    lowest_sch: bool
    least_threat: bool
    most_threat: bool
    lowest_order: bool
    highest_order: bool

class SelectorFilter:

    def __init__(self,
                finder: 'CardFinder',
                *,
                affects_target_if: Sequence[Callable[['Effect', 'CardFace'], bool]]=(),
                exclude: List['CardFace']|Literal["Trigger", "Attacker", "This", "Targets"]=[],
                another: bool|None=None, # Not `effect.this`

                share_trait_with_your_hero: bool=False,
                share_trait_with_your_identity: bool=False,
                corresponding: Literal["ActiveVillain"]|None=None,

                ################################################################################
                # Filter
                **kwargs: Unpack[FilterArgs],
        ):
        from game.card.face.card_face import CardFace
        from game.operate.worlds import Worlds
        from game.operate.filter import Filter

        self.finder = finder
        self.affects_target_if = tuple(affects_target_if)
        self.check_effect_fns: List[Callable[['Effect', 'CardFace'], bool]] = []

        ################################################################################
        #
        def filter_legal_targets(legal_faces: Sequence['CardFace'], effect: 'Effect') -> List['CardFace']:
            from game.player import Player
            initiator = effect.initiator

            corresponding_face = None
            if corresponding == "ActiveVillain":
                villain = Worlds.FindVillain(effect)
                if not villain:
                    return []
                else:
                    corresponding_face = villain.FindCorrespondingScheme()

            if share_trait_with_your_hero or share_trait_with_your_identity:
                if initiator.IsScenario():
                    return []
                if share_trait_with_your_hero and \
                    isinstance(initiator, Player) and \
                    not initiator.IsHero():
                    return []

            ################################################################################
            #
            excludes: List['CardFace'] = []
            if exclude == "This":
                excludes = [effect.this]
            elif exclude == "Trigger":
                if isinstance(effect.bind_message, TriggerMessage):
                    excludes = [effect.bind_message.trigger]
            elif exclude == "Attacker":
                if isinstance(effect.bind_message, AttackerMessageInternal):
                    attacker = effect.bind_message.attacker
                    if attacker:
                        excludes = [attacker]
            elif exclude == "Targets":
                if isinstance(effect.bind_message, TargetsMessage):
                    excludes = list(effect.bind_message.targets)
            else:
                excludes = exclude
            exclude_cards = [face.card for face in excludes]
            legal_faces = [face for face in legal_faces if face.card not in exclude_cards]

            ################################################################################
            #
            if (share_trait_with_your_hero or share_trait_with_your_identity) and \
                isinstance(initiator, Player):
                identity = initiator.GetIdentity()

            def filter_fn(face: 'CardFace') -> bool:
                if another and face == effect.this:
                    return False
                if not self.CheckFinder(face, effect):
                    return False
                # RR 1.8: for an ability with multiple effects on one target,
                # that target is valid when at least one declared effect can
                # affect it. Structural finder rules and the independent
                # attack/thwart/Crisis checks still have to pass.
                if self.affects_target_if and \
                    not any(fn(effect, face) for fn in self.affects_target_if):
                    return False
                if (share_trait_with_your_hero or share_trait_with_your_identity) and \
                    not face.ShareTrait(identity):
                    return False
                if corresponding_face != None and corresponding_face != face:
                    return False
                return True

            filter_faces = [face for face in legal_faces if filter_fn(face)]

            ################################################################################
            #
            if not filter_faces:
                return []

            filter_faces = Filter.All(
                filter_faces,
                CardFace,
                **kwargs
            )

            return filter_faces

        self.FilterLegalTargets = filter_legal_targets

    def CheckFinder(self, face: 'CardFace', effect: 'Effect|None') -> bool:
        if effect:
            for fn in self.check_effect_fns:
                if not fn(effect, face):
                    return False
        return not self.finder or self.finder.Check(face, effect)

    # def AddFinder(self, finder: 'CardFinder'):
    #     self.finder = finder & self.finder

    @property
    def target_must_include_traits(self):
        return self.finder.traits if self.finder else []

    @property
    def check_by_name(self) -> bool:
        return self.finder.check_by_name != [] if self.finder else False

    def AddParameter(self,
                    *,
                    canbe_exhaust: bool|None=None,
                    canbe_ready: bool|None=None,
                    has_non_health: bool|None=None,
                    canbe_heal: int|None=None,
                    check_effect_fn: Callable[['Effect', 'CardFace'], bool]|None=None, # Only call when has effect
                    ):
        from game.card.face.base import Unit2

        assert canbe_exhaust != None or \
            canbe_ready != None or \
            has_non_health != None or \
            canbe_heal != None or \
            check_effect_fn != None

        if canbe_exhaust != None:
            self.check_effect_fns.append(
                lambda effect, face: \
                    canbe_exhaust == face.CanExhaust()
            )
        if canbe_ready != None:
            self.check_effect_fns.append(
                lambda effect, face: \
                    canbe_ready == face.IsCanReadyBy(effect)
            )

        if has_non_health != None:
            self.check_effect_fns.append(
                lambda effect, face: \
                    Unit2.IsType(face) and has_non_health == bool(face.health <= 0)
            )

        if canbe_heal != None:
            self.check_effect_fns.append(
                lambda effect, face: \
                    Unit2.IsType(face) and face.CanHeath() and face.sustained >= canbe_heal
            )

        if check_effect_fn != None:
            self.check_effect_fns.append(check_effect_fn)
