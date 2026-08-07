from . import *

class HasVulnerable(HasAttribute):
    @override
    def __init__(self, paper: 'Paper') -> None:
        """
        Discard this character if it is stunned or confused.
        """
        self.printed_vulnerable: int = 0

        super().__init__(paper)

        self.RegisterAttribute("Vulnerable", "printed_vulnerable")
        self.RegisterInfoDict('vulnerable')

    @override
    def GetRuleAbilities(self) -> List['Ability']:
        def discard_vulnerable(effect: 'Effect', message: 'Message.AfterStatusCardPlaceOn') -> None:
            from game.operate.faces import Faces
            Faces.DiscardAll([effect.this], effect)

        return super().GetRuleAbilities() + [AbilityFactory.AfterStatusCardPlaceOn(
            AbilityType.ForcedInterrupt,
            "This",
            ["Confused", "Stunned"],
            discard_vulnerable,
            conditions=[
                lambda effect, message:
                    effect.this.CastTo(HasVulnerable).IsVulnerable() and
                    (
                        effect.this.IsStunned() or
                        effect.this.IsConfused()
                    ),
            ],
        ).SetName("Vulnerable")]

    ################################################################################
    #
    @override
    def OnResetKeywords(self, by_effect: 'Effect'):
        self.GainVulnerable(self.printed_vulnerable, by_effect)
        return super().OnResetKeywords(by_effect)

    @final
    def IsVulnerable(self) -> bool:
        return self.vulnerable > 0

    @final
    @property
    def vulnerable(self) -> int:
        return self.GetKeyword('Vulnerable')

    @final
    def GainVulnerable(self, diff: int, by_effect: 'Effect'):
        self.GainKeyword(diff, 'Vulnerable', by_effect)
