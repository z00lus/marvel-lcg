from . import *

class HasQuickstrike(HasAttribute):

    @override
    def __init__(self, paper: 'Paper') -> None:
        self.printed_quickstrike = 0

        super().__init__(paper)

        self.RegisterAttribute("Quickstrike", "printed_quickstrike")
        self.RegisterInfoDict('quickstrike')

    ################################################################################
    #
    @override
    def OnResetKeywords(self, by_effect: 'Effect'):
        self.GainQuickstrike(self.printed_quickstrike, by_effect)
        return super().OnResetKeywords(by_effect)

    @final
    def IsQuickstrike(self) -> bool:
        return self.quickstrike > 0

    @final
    @property
    def quickstrike(self) -> int:
        return self.GetKeyword('Quickstrike')

    @final
    def GainQuickstrike(self, diff: int, by_effect: 'Effect'):
        self.GainKeyword(diff, 'Quickstrike', by_effect)

class CanQuickstrike(HasQuickstrike):

    @override
    def GetRuleAbilities(self) -> List['Ability']:
        return super().GetRuleAbilities() + [AbilityFactory.AfterMinionEngagePlayer(
            AbilityType.ForcedResponse,
            "This",
            "YouHero",
            lambda effect, message:
                effect.this.CastTo(CanQuickstrike).ResolveQuickstrike(
                    message.engaged_player
                ),
            conditions=[
                lambda effect, message:
                    effect.this.CastTo(CanQuickstrike).IsQuickstrike(),
            ],
        ).SetName("Quickstrike")]

    @final
    def ResolveQuickstrike(self, player: 'Player'):
        from game.effect.rule import Quickstrike
        from game.card.face.base import Enemy
        if self.IsInPlay() and self.IsQuickstrike() and player.IsHero():
            effect = Quickstrike(self)
            if Enemy.IsType(self):
                self.DoAttackYou(player, effect)
            elif CanAttack.IsType(self):
                self.BasicAttack([player.GetIdentity()], effect)
