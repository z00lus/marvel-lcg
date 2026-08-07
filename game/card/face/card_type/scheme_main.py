from core import *
from game.card.face import *
from game.ability import *
from game.ability.factory import *
from game.message import *
from game.player import *
from cards.paper import Paper

@final
class MainScheme(Scheme2, HasStage, EncounterCard, FinalType):
    @override
    def __init__(self, paper: 'Paper') -> None:
        self.printed_target_threat: int|None = None
        self.target_threat = 0

        self.escalation_threat = 0
        self.is_completed = False

        super().__init__(paper)

        self.RegisterAttribute("TargetThreat", "printed_target_threat")
        self.RegisterAttribute("EscalationThreat", "escalation_threat")
        self.RegisterInfoDict('target_threat')
        self.RegisterInfoDict('escalation_threat')
        self.RegisterInfoDict('is_completed')

    @override
    def GetAbilities(self) -> List['Ability']:
        abilities: List['Ability'] = []
        if "<b>If this stage is completed, the players lose the game" in self.paper.text or \
            "<b>If this scheme is completed, the players lose the game" in self.paper.text:
            abilities = [
                AbilityFactory.IfThisSchemeStageIsCompletedPlayersLoseTheGame()
            ]
        return abilities + super().GetAbilities()

    @override
    def CheckPrintedValue(self):
        assert self.printed_target_threat == None or self.printed_target_threat >= 0
        assert self.escalation_threat >= 0
        return super().CheckPrintedValue()

    def ResetTargetThreat(self):
        self.target_threat = self.printed_target_threat

    @override
    def OnReset(self, message: 'Message.WhenCardReset_Text') -> None:
        self.ResetTargetThreat()
        self.is_completed = False
        return super().OnReset(message)

    @override
    def OnFlip(self, by_effect: 'Effect', origin_face: 'CardFace|None'):
        self.ResetTargetThreat()
        return super().OnFlip(by_effect, origin_face)

    @override
    def OnWhenCardRevealed(self, revealed_message: 'Message.WhenCardRevealed') -> None:
        if not self.IsInPlay():
            from game.effect.rule import GameRule
            first_player = self.card.world.GetFirstPlayer()
            self.PutIntoPlay(first_player, GameRule(self))
        return super().OnWhenCardRevealed(revealed_message)

    @override
    def OnAfterCardRevealedEnd(self, message: 'Message.AfterCardRevealedEnd') -> None:
        from game.effect.rule import Advance

        if self == self.card.printed_faces[0]:
            if self.printed_target_threat == None:
                effect = Advance(self)
                self.Advance(None, effect)
        return super().OnAfterCardRevealedEnd(message)

    @override
    def OnPutIntoPlay(self, message: 'Message.WhenCardPutIntoPlay') -> 'bool':
        from game.operate.faces import Faces
        world = self.card.world
        if self.card.area == world.area_schemes_main or \
            Faces.MoveAllTo([self], world.area_schemes_main, message.by_effect):
            return super().OnPutIntoPlay(message)
        else:
            return False

    ################################################################################
    #
    def Phase(self) -> None:
        # "21098a"
        # This scenario has two main scheme cards in play at the 
        # same time: Stage 1B and Stage 2B. Both main schemes 
        # are active each round. Encounter cards that refer to “the 
        # main scheme” refer to both main scheme cards. Each 
        # main scheme gains threat during step 1 of the villain 
        # phase, and they are each affected by any acceleration 
        # and crisis icons in play.
        # When a someone plays a card that refers to “the main 
        # scheme,” that card’s controller must choose which of the 
        # two schemes it is referring to. If a constant effect on a 
        # player card refers to “the main scheme,” that card always 
        # refers to the scheme card with the attachment “Focused 
        # Defense” attached to it.

        # This scenario has two villains: Proxima Midnight and 
        # Corvus Glaive. Each of these villains is paired with one 
        # of the main schemes. Stage 1B is identified as Proxima 
        # Midnight’s scheme, and stage 2B is identified as Corvus 
        # Glaive’s scheme. When either of the two villains schemes, 
        # place the threat on their matching main scheme card 
        # only. For example, when Proxima Midnight schemes, 
        # place the threat only on stage 1B. 
        from game.message import Message
        from game.effect.rule import MainSchemePhasePlaceThreat
        from game.operate.worlds import Worlds

        acceleration_icons: List['HasAccelerationIcon'] = []
        acceleration_tokens: List['CanAccelerationToken'] = []

        for face in Worlds.GetAccelerationIconFaces(self.card.GetGameArea()):
            acceleration_icons.append(face)

        for face in Worlds.GetAccelerationTokenFaces(self.card.GetGameArea()):
            # 21-the_mad_titans_shadow_rulebook
            # SCENARIO #2 - TOWER DEFENSE
            # This scenario has two main scheme cards in play at the
            # same time: Stage 1B and Stage 2B. Both main schemes
            # are active each round. Encounter cards that refer to “the
            # main scheme” refer to both main scheme cards. Each
            # main scheme gains threat during step 1 of the villain
            # phase, and they are each affected by any acceleration
            # and crisis icons in play.
            acceleration_tokens.append(face)

        message = Message.CalcMainSchemeEscalation(self, self.escalation_threat, acceleration_icons, acceleration_tokens)
        message.Send()

        self.PlaceThreatInternal(message.escalation_threat, MainSchemePhasePlaceThreat(self))

    def Advance(self, to_face: Literal["2A", "3A"]|CardFace|None, by_effect: 'Effect') -> None:
        self.card.world.AdvanceMainScheme(self, to_face, by_effect)

    ################################################################################
    #
    @override
    def RemoveThreatInternal(self, by_face: 'CardFace', value: Literal["All"]|INT_TYPE, by_effect: 'Effect', thw_message: 'Message.WhenSchemeBeingThwart|None' = None) -> int:
        from game.operate.worlds import Worlds
        ignored_crisis = False
        ignored_patrol = False

        crisis_faces = Worlds.GetCrisisFaces(self.card.GetGameArea())
        if crisis_faces:
            if not by_effect.IsIgnoreKeyword('Crisis', by_effect):
                message = Message.IconsActivate_Text(self, crisis_faces, 'Crisis')
                message.Send()
                return 0
            else:
                ignored_crisis = True

        patrol_faces: Sequence[CardFace] = []
        if by_effect.IsIgnoreKeyword('Patrol', by_effect):
            patrol_faces = MainScheme.GetPatrolFaces(by_effect)
            if patrol_faces:
                ignored_patrol = True

        ret_value = super().RemoveThreatInternal(by_face, value, by_effect, thw_message)

        if ignored_crisis:
            ignore_message = Message.AfterIgnoreKeywordOnCard(by_face, crisis_faces, "Crisis")
            ignore_message.Send()

        if ignored_patrol:
            ignore_message = Message.AfterIgnoreKeywordOnCard(by_face, patrol_faces, "Patrol")
            ignore_message.Send()

        return ret_value

    @override
    def PlaceThreatInternal(self, value: INT_TYPE, by_effect: 'Effect', sch_message: 'Message.WhenUnitWouldScheme|None'=None) -> 'Message.AfterSchemePlaceThreat|None':
        from game.effect.rule import Advance
        from game.message import Message
        place_message = super().PlaceThreatInternal(value, by_effect, sch_message)
        if place_message and self.target_threat != None:
            if self.threat >= self.target_threat and not self.is_completed:
                would_complete_message = Message.WhenMainSchemeStageWouldBeCompleted(self, sch_message)
                would_complete_message.Send()
                if not would_complete_message.is_be_instead:
                    self.is_completed = True
                    when_complete_message = Message.WhenMainSchemeStageCompleted(self, would_complete_message)
                    when_complete_message.Send()
                    effect = Advance(self)
                    self.Advance(None, effect)
                    after_message = Message.AfterMainSchemeCompleted(self, when_complete_message)
                    after_message.Send()
            return place_message
        return None

    @staticmethod
    def GetPatrolFaces(effect: 'Effect') -> Sequence['CardFace']:
        if effect.initiator.IsPlayer():
            return [x for x in effect.GetInitiator().GetEngagedMinions() if x.IsPatrol()]
        else:
            return []

    @override
    def CanBeThwartBy(self, effect: 'Effect') -> bool:
        from game.operate.worlds import Worlds
        main_scheme = Worlds.FindMainScheme(self)
        if main_scheme == self:
            if Worlds.GetCrisisFaces(self.card.GetGameArea()):
                if not effect.IsIgnoreKeyword('Crisis', effect):
                    return False
            if MainScheme.GetPatrolFaces(effect) != []:
                if not effect.IsIgnoreKeyword('Patrol', effect) and effect.IsPlayerInitiator():
                    return False
        return super().CanBeThwartBy(effect)

    def GainTargetThreatValue(self, value: int, effect: 'Effect'):
        if self.target_threat != None:
            self.target_threat += value
