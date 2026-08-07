from . import *

class HasRetaliate(HasAttribute):
    @override
    def __init__(self, paper: 'Paper') -> None:
        self.printed_retaliate = 0

        super().__init__(paper)

        self.RegisterAttribute("Retaliate", "printed_retaliate")
        self.RegisterInfoDict('retaliate')

    @override
    def OnResetKeywords(self, by_effect: 'Effect'):
        self.GainRetaliate(self.printed_retaliate, by_effect)
        return super().OnResetKeywords(by_effect)

    ################################################################################
    #
    @final
    def GainRetaliate(self, diff: int, by_effect: 'Effect'):
        self.GainKeyword(diff, 'Retaliate', by_effect)

    @final
    @property
    def retaliate(self) -> int:
        return self.GetKeyword('Retaliate')

class CanRetaliate(HasRetaliate):

    @override
    def GetRuleAbilities(self) -> List['Ability']:
        return super().GetRuleAbilities() + [Ability(
            AbilityType.ForcedResponse,
            Message.AfterUnitAttackUnit,
            [
                lambda effect, message:
                    message.attacked == effect.this and
                    effect.this.CastTo(CanRetaliate).CanResolveRetaliate(
                        message.would_atk_unit_message
                    ),
            ],
            lambda effect, message:
                effect.this.CastTo(CanRetaliate).ResolveRetaliate(
                    message.would_atk_unit_message
                ),
            is_local=True,
        ).SetName("Retaliate")]

    @final
    def CanResolveRetaliate(self, atk_message: 'Message.WhenUnitWouldAttackUnit') -> bool:
        attacker = atk_message.attacker
        return self.retaliate > 0 and \
            self.IsInPlay() and \
            bool(attacker) and \
            attacker.IsInPlay() and \
            not attacker.IsDefeated() and \
            not atk_message.IsRanged() and \
            not self.IsDefeated() and \
            not atk_message.IsIgnoreRetaliate()

    @final
    def ResolveRetaliate(self, atk_message: 'Message.WhenUnitWouldAttackUnit'):
        from game.effect.rule import Retaliate

        if CanRetaliate.CanResolveRetaliate(self, atk_message):
            attacker = atk_message.attacker
            assert attacker
            return attacker.TakeDamage(self, self.retaliate, Retaliate(self))
        attacker = atk_message.attacker
        if self.retaliate > 0 and self.IsInPlay() and attacker and \
            attacker.IsInPlay() and not attacker.IsDefeated():
            ignore_message = Message.AfterIgnoreKeywordOnCard(attacker, [self], "Retaliate")
            ignore_message.Send()
        return None
