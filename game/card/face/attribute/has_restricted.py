from . import *

class HasRestricted(HasAttribute):
    @override
    def __init__(self, paper: 'Paper') -> None:
        self.printed_restricted = 0

        super().__init__(paper)

        self.RegisterAttribute("Restricted", "printed_restricted")
        self.RegisterInfoDict('restricted')

    # @override
    # def GetAbilities(self) -> List['Ability']:
    #     return super().GetAbilities()

    @override
    def GetRuleAbilities(self) -> List['Ability']:
        return super().GetRuleAbilities() + [AbilityFactory.AfterCardEnterPlay(
            AbilityType.ForcedResponse,
            "This",
            lambda effect, message:
                effect.this.CastTo(HasRestricted).CheckRestrictedLimit([]),
            conditions=[
                lambda effect, message:
                    bool(effect.this.CastTo(HasRestricted).restricted),
            ],
        ).SetName("Restricted")]

    ################################################################################
    #
    def CheckRestrictedLimit(self, gain_faces: List['CardFace']) -> bool:
        player = self.GetControlByPlayer()
        return player.limit_restricted.CheckLimit(gain_faces)

    @override
    def OnNotTreatAsIfBlank(self, message: 'Message.WhenCardTreatAsIfBlank') -> None:
        if self.restricted:
            self.CheckRestrictedLimit([])
        return super().OnNotTreatAsIfBlank(message)

    @override
    def OnAfterCardLeavePlay(self, message: 'Message.AfterCardLeavePlay') -> None:
        player = message.from_area.GetOwner()
        if Player.IsType(player):
            player.limit_restricted.CheckLimit([])
        return super().OnAfterCardLeavePlay(message)

    @override
    def OnAfterCardFlip(self, message: 'Message.AfterCardFlip'):
        face = message.to_face
        if face and HasRestricted.IsType(face):
            if face.restricted:
                self.CheckRestrictedLimit([])
        super().OnAfterCardFlip(message)

    ################################################################################
    #
    @override
    def OnResetKeywords(self, by_effect: 'Effect'):
        self.GainRestricted(self.printed_restricted, by_effect)
        return super().OnResetKeywords(by_effect)

    @final
    def GainRestricted(self, diff: int, by_effect: 'Effect'):
        self.GainKeyword(diff, 'Restricted', by_effect)
        if diff > 0:
            self.CheckRestrictedLimit([])

    @final
    @property
    def restricted(self) -> int:
        return self.GetKeyword('Restricted')
