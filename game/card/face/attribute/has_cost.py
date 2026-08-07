from . import *

class HasCost(HasAttribute):

    @override
    def __init__(self, paper: 'Paper') -> None:
        self.printed_cost = Cost("0")
        self.has_printed_cost = False
        self.printed_cost_is_x = False
        self.requirement = Cost("0")
        
        # self.paid_resources = Resources("0")
        super().__init__(paper)

        def parse(value: str):
            self.has_printed_cost = True
            if value == "X":
                self.printed_cost_is_x = True
                self.printed_cost = Cost("0")
            elif "*" in value:
                self.printed_cost = Cost.FromText(str(self.FormatPlayerNumValue(value)))
            else:
                self.printed_cost = Cost.FromText(value)
        self.RegisterAttribute("Cost", parse)

        def parse2(value: str):
            self.requirement = Cost.FromText(value)
        self.RegisterAttribute("Requirement", parse2)

    def GetPrintedCostWithRequirement(self) -> 'Cost':
        return self.printed_cost - self.requirement.val + self.requirement

    # @override
    # def OnLeavedPlay(self, by_effect: 'Effect'):
    #     self.paid_resources = Resources("0")
    #     return super().OnLeavedPlay(by_effect)

    def SetPaidResources(self, res: 'Resources'):
        pass

    ################################################################################
    #
    def GetTurnPlayEffects(self) -> List['Effect']:
        return [x for x in self.effects if x.ability.is_play and x.ability.when == Message.WhenPlayerInTurn]

    @override
    def CanPlayBy(self, player: 'Player') -> bool:
        from game.event.manager import EventManager
        from game.effect.rule import GameRule
        effects = self.effect.Find(func_name="Play", when=Message.WhenPlayerInTurn)
        message = Message.WhenPlayerLikeInTurn(player, GameRule(player.GetIdentity()))
        message.Send()

        self.card.can_state.is_like_in_hand = True
        # like_in_hand_effect = self.SetLikeInHand()
        filtered_effects = EventManager.FilterAvailableEffects(message, effects, player, self.card.world, None)
        # like_in_hand_effect.UnRegisterSelf()
        self.card.can_state.is_like_in_hand = None

        return filtered_effects != []
