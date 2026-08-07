from core import *
from game.player.user import *
from game.deck import *
from game.effect import *
from game.world import *

class Scenario(User):
    def __init__(self, name: str, world: 'World'):
        super().__init__("scenario", world)
        self.is_scenario = True
        self.name: str = name
        from game.deck import Deck2, DeckType
        from game.card.face.base import Villain
        from game.card.face.card_face import CardFace

        self.area_villain = Deck2(self, DeckType.VillainArea, Villain)
        self.villain_deck = Deck2(self, DeckType.VillainDeck, Villain)

        self.encounter_deck = Deck2(self, DeckType.EncounterDeck, CardFace)
        self.encounter_discard_pile = Deck2(self, DeckType.EncounterDiscardPile, CardFace)

        def process_after_shuffle(deck: 'Deck', by_effect: 'Effect'):
            from game.effect.rule import GameRule
            from game.operate.worlds import Worlds

            scheme = Worlds.FindMainScheme(by_effect)
            if scheme:
                scheme.PlaceAccelerationToken(1, GameRule(scheme))
        self.encounter_deck.BindDiscardPile(self.encounter_discard_pile, process_after_shuffle)

    def GetVillain(self, game_area: 'GameArea|None') -> 'Villain|None':
        if self.area_villain.GetSize() == 0:
            return None
        game_area = self.world.CastGameArea(game_area)

        from game.message import Message
        message = Message.GettingVillain(game_area, self.world)
        message.Send()
        villain = message.return_value
        if villain:
            return villain

        for villain in self.area_villain.Get():
            if villain.IsActive():
                return villain

        for villain in self.area_villain.Get():
            if not game_area or villain.card.GetGameArea() == game_area:
                return villain
        # assert False, f"{game_area=}"
        return None

    def IsVillainReady(self) -> bool:
        return self.area_villain.GetSize() > 0

    def SelectVillain(self, villains: Sequence[str]):
        from game.card.factory import CardFactory
        CardFactory.GenerateCards(villains, self.villain_deck, self.world)
        if self.villain_deck.GetSize() > 0:
            self.name = self.villain_deck.Get(False)[0].name
            # self.AdvanceVillainStage(None)

    def GetNextVillain(self, prev_villain: 'Villain') -> 'Villain|None':
        for villain in self.villain_deck.Get(False):
            if villain.IsName(prev_villain.name, check_all_face=True):
                return villain
        return None

    def AdvanceVillainStage(self, prev_villain: 'Villain', by_effect: 'Effect', to_villain: 'Villain|None'=None, move_prev_villain_to: 'Deck|None'=None) -> bool:
        from game.message import Message
        from game.effect.rule import GameRule
        from game.card.face.base import Villain
        from game.operate.faces import Faces

        if self.world.is_game_over:
            return False

        # next villain will use the prev_villain card for same object_id
        def remove_prev_villain(prev_villain: 'Villain'):
            if move_prev_villain_to == None:
                if prev_villain.victory:
                    # Should aleady been move
                    if not prev_villain.card.area.flags.is_victory_display:
                        Faces.AddToVictoryDisplay([prev_villain], GameRule(prev_villain.card.face))
                    # next_villain.card.MoveToArea(self.world.victory_display, GameRule(next_villain.card.face))
                else:
                    Faces.RemoveAllFromGame([prev_villain], GameRule(prev_villain.card.face))
            else:
                Faces.MoveAllTo([prev_villain], move_prev_villain_to, GameRule(prev_villain.card.face))

        def advance(prev_villain: 'Villain', next_villain: 'Villain'):
            villain_card = prev_villain.card
            world = by_effect.world

            would_message = Message.WhenVillainWouldAdvance(prev_villain)
            would_message.Send()

            if not next_villain.IsName(prev_villain.name, check_all_face=True):
                next_villain.PutIntoPlay("FirstPlayer", by_effect)
                new_villain = next_villain
                # new_villain.SetEncounterDeck(prev_villain.encounter_deck)
                remove_prev_villain(prev_villain)
                message = Message.WhenVillainAdvance(new_villain, by_effect)
                message.Send()
            else:
                from game.card.factory import CardFactory

                old_faces: List[CardFace] = []
                for face in prev_villain.card.printed_faces:
                    old_faces.append(CardFactory.CreateFace(face.paper, world))

                back_faces: List[CardFace] = []
                first_faces: List[CardFace] = []
                for face in next_villain.card.printed_faces:
                    if face.IsName(prev_villain.name):
                        first_faces.append(CardFactory.CreateFace(face.paper, world))
                    else:
                        back_faces.append(CardFactory.CreateFace(face.paper, world))
                assert first_faces, f"{next_villain.card.printed_faces=}"

                next_villain.card.SetAsCard(old_faces[0], old_faces[1:], True)

                first_face = None
                if len(first_faces) == 1:
                    first_face = first_faces[0]
                else:
                    first_faces = sorted(first_faces, key=lambda face: face.GetShareTraitNum(prev_villain))
                    first_face = first_faces[-1]
                    first_faces.remove(first_face)
                    back_faces += first_faces

                new_villain = villain_card.SetAsCard(first_face, back_faces, True)

                rule_effect = GameRule(new_villain)

                new_villain.card.state.is_advancing = True
                prev_villain.OnBeforeSwap(rule_effect, new_villain)
                new_villain.card.state.is_advancing = False

                new_villain = new_villain.CastTo(Villain)
                CardFactory.CardRegisterEffects(villain_card)

                # Fix `try_shuffle_deck` in Play Rule
                new_villain.SetEncounterDeck(prev_villain.encounter_deck)
                # If we remove the old card before, the UI will look strange
                remove_prev_villain(next_villain)
                
                new_villain.ResetHealth(rule_effect)
                message = Message.WhenVillainAdvance(new_villain, by_effect)
                message.Send()

                new_villain.OnAfterSwap(rule_effect, call_reveal=True)
                # new_villain.BeforeFlip(GameRule(new_villain))
                # new_villain.OnFlip(GameRule(new_villain), None)
                # new_villain.card.is_swapping = False
                # new_villain.OnAfterFlip(GameRule(new_villain))

            after_message = Message.AfterVillainAdvanced(new_villain, by_effect, message)
            after_message.Send()
        pass

        if to_villain:
            advance(prev_villain, to_villain)
        elif self.villain_deck.GetSize() > 0:
            next_villain = self.GetNextVillain(prev_villain)

            if next_villain == None:
                remove_prev_villain(prev_villain)
                return False

            advance(prev_villain, next_villain)
        else:
            if self.world.aside_deck.FindCard(card_type=Villain) == None and \
                self.area_villain.FindCards(card_type=Villain) == [prev_villain]:
                self.world.game_over.SetGameOverByRule("The Final Stage of the Villain was Defeated")
            if not self.world.is_game_over:
                assert prev_villain, f"{self=}"
                if prev_villain.IsInPlay():
                    Faces.RemoveAllFromGame([prev_villain], GameRule(prev_villain))
        return self.world.is_game_over

    @override
    def GetGameArea(self) -> 'GameArea':
        world = self.world
        if not world.is_game_started:
            return world.GetFirstGameArea()
        if self.IsVillainReady():
            if world.current_player:
                return world.current_player.GetIdentity().card.GetGameArea()
            # else:
            #     return self.GetVillains()[0].card.GetGameArea()
        return world.GetFirstGameArea()

    @override
    def GetRoleCharacter(self):
        villain = self.GetVillain(None)
        assert villain != None
        return villain

    ################################################################################
    #
    @classmethod
    def IsType(cls, user: 'User|None') -> TypeGuard['Scenario']:
        if user == None:
            return False
        return not user.IsPlayer()
