from . import *

class HasSurge(HasAttribute):

    @override
    def __init__(self, paper: 'Paper') -> None:
        self.printed_surge = 0

        super().__init__(paper)

        self.RegisterAttribute("Surge", "printed_surge")
        self.RegisterInfoDict('surge')

    @override
    def OnResetKeywords(self, by_effect: 'Effect'):
        self.GainSurge(self.printed_surge, by_effect)
        return super().OnResetKeywords(by_effect)

    @final
    def GainSurge(self, diff: int, by_effect: 'Effect'):
        self.GainKeyword(diff, 'Surge', by_effect)

    @final
    @property
    def surge(self) -> int:
        return self.GetKeyword('Surge')

class CanSurge(HasSurge):

    @final
    def ResolveSurge(self, player: 'Player') -> 'Effect|None':
        if not self.surge:
            return None

        from game.message import Message
        from game.effect.rule import Surge
        surge_message = Message.WhenSurgeWouldBeResolved(self, player)
        surge_message.Send()
        if not surge_message.is_be_instead:
            effect = Surge(self)
            # Rules Reference 1.8: Surge deals a facedown card. The normal
            # encounter queue reveals it only after the original reveal and
            # all responses have finished, or during the next villain phase
            # when Surge resolves outside step four.
            player.DealEncounterCards(1, effect)
            return effect
        return None
