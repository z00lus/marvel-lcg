from typing import Final
from core import *
from game.render.symbol import Symbol
from game.element.cost import Cost
from game.element.rbyg import ResRBYG
from game.player import *

class Resources:

    RBYG: Final = ResRBYG.RBYG
    RBY: Final = ResRBYG.RBY
    RES_TEXT: Final = {'r': Symbol.r_r_physical, 'g': Symbol.r_g_wild, 'b': Symbol.r_b_mental, 'y': Symbol.r_y_energy}
    RBYG_LIST: List[ResRBYG.RBYG] = ["R", "B", "Y", "G"]

    # if `text` like "R", then `total` == self.r + self.b + self.y + self.g
    # e.g. "0" "RR" "RBY"
    def __init__(self, rbyg: Literal[
                    "-1", "-2", "-3",
                    "0",
                    "R", "B", "Y", "G",
                    "BB", "GG",
                    "RRR", "BBB", "YYY",
                ]|ResRBYG,
                *,
                reduce: int|None=None, # > 0
                ) -> None:
        if isinstance(rbyg, ResRBYG):
            self.rbyg = rbyg
        else:
            self.rbyg = ResRBYG.FromText(rbyg)

        if isinstance(rbyg, str):
            text = rbyg.lower()
            if text and text[0] == '-' and text[1:].isdigit():
                assert reduce == None
                reduce = int(text[1:])

        if reduce != None:
            assert reduce >= 0
        self.reduce: Final = reduce if reduce != None else 0

        # Text
        self.text_legacy = Symbol.Clean(self.color_text)

    def __repr__(self) -> str:
        return self.color_text

    @property
    def text(self) -> str:
        return self.text_legacy

    @property
    def color_text(self) -> str:
        if self.reduce:
            return str(-1 * self.reduce)
        else:
            return self.rbyg.color_text

    @property
    def val(self) -> int:
        return self.rbyg.total

    ################################################################################
    #
    def __mul__(self, val: int) -> 'Resources':
        return Resources(
            self.rbyg * val,
            reduce=self.reduce * val,
        )

    def __add__(self, other: 'Resources') -> 'Resources':
        return Resources(
            self.rbyg + other.rbyg,
            reduce=self.reduce+other.reduce
        )

    def __sub__(self, other: 'Resources') -> 'Resources':
        return Resources(
            self.rbyg - other.rbyg,
            reduce=self.reduce-other.reduce
        )

    ################################################################################
    #
    @staticmethod
    def FromText(text: str) -> 'Resources':
        return Resources(Cast(Any, text))

    ################################################################################
    #
    def IsMatchCost(self, cost: 'Cost') -> bool:
        if cost.rule.or_res:
            if self.IsMatchCost(cost.rule.or_res):
                return True
        if self.reduce != 0:
            cost -= self.reduce
        if cost.rule.up_to:
            assert cost.GetTypeKinds() <= 1
            return self.val <= cost.val
        elif self.val >= cost.val:
            green = self.rbyg.g - cost.rbyga.g

            def check_value(value: int):
                nonlocal green
                if value < 0:
                    green += value

            check_value(self.rbyg.r - cost.rbyga.r)
            check_value(self.rbyg.b - cost.rbyga.b)
            check_value(self.rbyg.y - cost.rbyga.y)

            if green < 0:
                return False
            else:
                if cost.rule.same_type:
                    return self.rbyg.IsSameType()
                elif cost.rule.different_type:
                    return self.rbyg.IsDifferentType() >= cost.val 
                return True
        return False

    @staticmethod
    def FindCostAllocations(resources: 'Resources', costs: Sequence['Cost']) -> List[List['Resources']]:
        """Return every way generated resources can pay simultaneous costs."""
        from game.element.rbyg import ResRBYG

        if not costs:
            return [[]]

        def distributions(value: int, size: int) -> List[Tuple[int, ...]]:
            if size == 1:
                return [(value,)]
            result: List[Tuple[int, ...]] = []
            for first in range(value + 1):
                for rest in distributions(value - first, size - 1):
                    result.append((first,) + rest)
            return result

        size = len(costs)
        allocations: List[List[Resources]] = []
        seen: Set[Tuple[Tuple[int, int, int, int, int], ...]] = set()

        for r_values in distributions(resources.r, size):
            for b_values in distributions(resources.b, size):
                for y_values in distributions(resources.y, size):
                    for g_values in distributions(resources.g, size):
                        allocation: List[Resources] = []
                        for index in range(size):
                            allocation.append(Resources(
                                ResRBYG(
                                    r_values[index],
                                    b_values[index],
                                    y_values[index],
                                    g_values[index],
                                ),
                                # Reductions modify the original resource
                                # cost, not a separate Spend cost.
                                reduce=resources.reduce if index == 0 else 0,
                            ))
                        if not all(
                            allocation[index].IsMatchCost(cost)
                            for index, cost in enumerate(costs)
                        ):
                            continue
                        key = tuple(
                            (res.r, res.b, res.y, res.g, res.reduce)
                            for res in allocation
                        )
                        if key not in seen:
                            seen.add(key)
                            allocations.append(allocation)
        return allocations

    @staticmethod
    def CanPayCosts(resources: 'Resources', costs: Sequence['Cost']) -> bool:
        return bool(Resources.FindCostAllocations(resources, costs))

    def OnlyHasColor(self, text: "Resources.RBY") -> bool:
        return self.rbyg.OnlyHasColor(text)

    # When `convert_green_res`, 'G' will not be a type of resources
    # `convert_green_res` == True
    #   self 'G' text 'R' return True ('G' -> 'R')
    # `convert_green_res` == False
    #   self 'G' text 'R' return False ('G' is still 'G')
    def HasOneOfColor(self, texts: List["Resources.RBYG"], *, convert_green_res: bool = True) -> bool:
        for text in texts:
            if self.GetColor(text, convert_green_res=convert_green_res) > 0:
                return True
        return False

    def HasColorPrinted(self, text: "Resources.RBYG") -> bool:
        return self.GetColor(text, convert_green_res=False) > 0

    def HasColor(self, text: "Resources.RBYG", *, convert_green_res: bool=True) -> bool:
        if "G" == text:
            convert_green_res = False
        return self.GetColor(text, convert_green_res=convert_green_res) > 0

    def GetColor(self, text: "Resources.RBYG", *, convert_green_res: bool=True) -> int:
        return self.rbyg.GetColor(text, convert_green_res=convert_green_res)

    def CanPayThisCost(self, cost: 'Cost') -> bool:
        if cost.rule.or_res:
            return True
        if self.reduce > 0:
            return True
        if self.val == 0:
            return False
        return self.rbyg.CanPayThisCost(cost.rbyga)

    # Green is a type, return [0, 4]
    def GetResourceIconTypes(self) -> int:
        return self.rbyg.GetTypeKindsInternal(True)

    def Copy(self) -> 'Resources':
        from copy import copy
        return copy(self)

    ################################################################################
    #
    @property
    def r(self) -> int:
        return self.rbyg.r
    @property
    def b(self) -> int:
        return self.rbyg.b
    @property
    def y(self) -> int:
        return self.rbyg.y
    @property
    def g(self) -> int:
        return self.rbyg.g
