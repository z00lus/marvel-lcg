from core import *
from game.card.face import *
from game.effect import *
from game.element.resources import Resources
from game.element.cost import Cost

class TargetCost:

    @dataclass
    class Payment:
        cost: 'Cost'
        component_costs: List['Cost']
        # str, "RYB", ~~UI only~~, show can generate res of each effect
        # these effects can do pay, and the str store the resources they can generate
        payments: List[Dict['Effect', str]]
        cost_check: Dict['Effect', 'Effect']

    def __init__(self) -> None:
        self.target_cost: Dict['CardFace|None', 'TargetCost.Payment'] = {}
        self.only_none_target = False

    def SetNoneTargetOnly(self):
        self.only_none_target = True

    def IsEmpty(self) -> bool:
        return self.target_cost == {}

    def HasTarget(self, face: 'CardFace|None') -> bool:
        return face in self.target_cost

    def GetCost(self, face: 'CardFace|None') -> 'Cost':
        if self.only_none_target:
            return self.target_cost[None].cost
        return self.target_cost[face].cost

    def GetPayment(self, face: 'CardFace|None') -> 'TargetCost.Payment':
        if self.only_none_target:
            return self.target_cost[None]
        return self.target_cost[face]

    @staticmethod
    def CanPay(payment: 'TargetCost.Payment') -> bool:
        """Return whether some available resource combination pays a cost."""
        available: Dict[Tuple[int, int, int, int, int], Resources] = {}

        def add(resources: 'Resources') -> bool:
            key = (
                resources.r,
                resources.b,
                resources.y,
                resources.g,
                resources.reduce,
            )
            available[key] = resources
            if payment.component_costs:
                return Resources.CanPayCosts(resources, payment.component_costs)
            return resources.IsMatchCost(payment.cost)

        if add(Resources("0")):
            return True

        for payment_option in payment.payments:
            current = list(available.values())
            for resources_text in payment_option.values():
                resources = Resources.FromText(resources_text)
                for accumulated in current:
                    if add(accumulated + resources):
                        return True
        return False

    def HasPayableTarget(self) -> bool:
        return any(TargetCost.CanPay(payment) for payment in self.target_cost.values())

    def UpdateCost(self, face: 'CardFace|None', diff: 'int'):
        self.target_cost[face].cost += diff

    # def GetEffectsTotalResText(self, face: 'CardFace|None', paid_effects: List['Effect']) -> 'Resources':
    #     res = Resources("0")
    #     for pay_info in self.target_cost[face].payments:
    #         for effect in paid_effects:
    #             if effect in pay_info:
    #                 res += Resources(pay_info[effect])
    #                 break
    #     return res

    def AddTarget(self, face: 'CardFace|None', cost: 'Cost', *, component_costs: Sequence['Cost']=()) -> None:
        self.target_cost[face] = TargetCost.Payment(cost, list(component_costs), [], {})

    def AddPayment(self, face: 'CardFace|None', cost_effect: 'Effect', cost: 'Resources', check_effect: 'Effect') -> None:
        # pay_info = {effect: res.text_legacy}
        # # assert self.for_targets != []
        # self.for_effect.for_select_target_dict[].pay_info.append(pay_info)
        self.target_cost[face].payments.append({cost_effect: cost.text_legacy})
        self.target_cost[face].cost_check[cost_effect] = check_effect

    def GetAllPayEffects(self) -> List['Effect']:
        effects: List['Effect'] = []
        for face in self.target_cost:
            for effect_str in self.target_cost[face].payments:
                for effect in effect_str:
                    if effect not in effects:
                        effects.append(effect)
        return effects

    def GetResourcesForEffects(self, face: 'CardFace|None', paid_effects: Sequence['Effect']) -> 'Resources|None':
        """Calculate a selected payment without applying any resource effects.

        A payment offer can become stale between rendering the choice and
        confirming it (for example after a target-dependent discount changes).
        Treat an effect that is no longer valid for the selected target as a
        failed payment instead of raising during ability initiation.
        """
        resources = Resources("0")
        payment = self.GetPayment(face)
        for paid_effect in paid_effects:
            found = False
            for effect_resources in payment.payments:
                if paid_effect in effect_resources:
                    resources += Resources.FromText(effect_resources[paid_effect])
                    found = True
                    break
            if not found:
                return None
        return resources

    def FindPayEffect(self, target: 'CardFace|None', effect_id: int) -> 'Effect|None':
        for effect_res in self.GetPayment(target).payments:
            for effect in effect_res:
                if effect.object_id == effect_id:
                    return effect
        return None
