from . import *

class HasPermanent(HasAttribute):
    @override
    def __init__(self, paper: 'Paper') -> None:
        self.printed_permanent = False

        super().__init__(paper)

        self.RegisterAttribute("Permanent", "printed_permanent", bool)
        self.RegisterInfoDict('permanent')

    ################################################################################
    #
    @override
    def OnWhenCardLeavePlay(self, message: 'Message.WhenCardLeavePlay') -> bool:
        from game.player import Player
        if self.permanent:
            by_effect = message.by_effect
            owner = self.GetOwner()
            bind_face = self.GetBindFace()
            bind_controller = bind_face.GetControlBy() if bind_face else None
            if isinstance(owner, Player) and owner.is_eliminated:
                pass
            elif isinstance(bind_controller, Player) and bind_controller.is_eliminated:
                pass
            elif self.paper.set_name != by_effect.this.paper.set_name:
                return False
        return super().OnWhenCardLeavePlay(message)

    @override
    def OnResetKeywords(self, by_effect: 'Effect'):
        self.GainPermanent(self.printed_permanent, by_effect)
        return super().OnResetKeywords(by_effect)

    @final
    def GainPermanent(self, diff: int, by_effect: 'Effect'):
        self.GainKeyword(diff, 'Permanent', by_effect)

    @final
    @property
    def permanent(self) -> bool:
        return self.GetKeyword('Permanent') > 0
