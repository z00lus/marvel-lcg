from typing import TypeAlias
from core import *
from typing_extensions import Unpack
from game.card.face import *
from game.card import *
from game.player import *
from game.effect import *
from game.world.game_area import *
from game.object import Object
from game.deck.deck_type import DeckType

CardFaceType: TypeAlias = 'CardFace'

@final
class Deck2(Generic[TC], Object):
    def __init__(self, owner: 'Player|Scenario|Card', deck_type: DeckType, card_type: 'Type[TC]', *, related_player: 'Player|None'=None) -> None:
        from game.card import Card

        self.cards: List[Card] = []
        self.removed_cards: List[Card] = []
        self.deck_type = deck_type
        self.flags = deck_type.flags
        self.on_discards = False
        self.bind_card: 'Card|None' = None
        self.bind_owner: Player|Scenario
        self.card_type = card_type
        self.bind_discard_pile: 'Deck|None' = None
        self.process_after_shuffle: Callable[['Deck', 'Effect'], Any] = lambda deck, effect: None
        self.play_area: 'Player|None'

        self.shuffle_with_discard_count = 0

        self.for_undo_shuffle: List[Card] = []

        if isinstance(owner, Card):
            self.bind_card = owner
            self.bind_owner = self.bind_card.GetOwner()
        else:
            self.bind_owner = owner

        if related_player == None and isinstance(self.bind_card, Player):
            self.play_area = self.bind_card
        else:
            self.play_area = related_player

        world = self.bind_owner.world
        super().__init__('deck', world)

    def __repr__(self) -> str:
        if self.bind_card:
            return f"{self.bind_card.face}'s {self.deck_type.name}<{self.GetSize()}>"
        elif self.GetOwner() and not self.GetOwner().is_scenario:
            return f"{self.GetOwner()}'s {self.deck_type.name}<{self.GetSize()}>"
        else:
            return f"{self.deck_type.name}<{self.GetSize()}>"

    def GetIndex(self, face: 'CardFace') -> int:
        return self.cards.index(face.card)

    def GetOwner(self) -> 'Player|Scenario':
        if self.bind_card:
            if self.bind_card.IsOnField():
                player = self.bind_card.GetController()
                assert player != None
                return player
            else:
                return self.bind_owner
        else:
            return self.bind_owner

    def GetOwnerPlayer(self) -> 'Player':
        owner = self.GetOwner()
        assert isinstance(owner, Player)
        return owner

    def BindDiscardPile(self, deck: 'Deck', process_after_shuffle: Callable[['Deck', 'Effect'], Any]):
        assert self.flags.is_deck or self.flags.is_set_aside
        self.bind_discard_pile = deck
        self.process_after_shuffle = process_after_shuffle
    def Clear(self):
        from game.effect.rule import GameRule
        from game.operate.faces import Faces
        Faces.RemoveAllFromGame(self.Get(), GameRule(self.GetOwner().GetRoleCharacter()))
    def Destroy(self):
        for card in self.cards:
            card.Destroy()
        self.cards = []
    def MarkAsRemoved(self, card: 'Card') -> None:
        self.removed_cards.append(card)
        self.cards.remove(card)
    def UnMarkAsRemoved(self, card: 'Card') -> None:
        if card in self.removed_cards:
            self.removed_cards.remove(card)
            self.cards.append(card)
    def Remove(self, card: 'Card') -> None:
        if card in self.removed_cards:
            self.removed_cards.remove(card)
        else:
            self.cards.remove(card)
    def Append(self, card: 'Card') -> None:
        self.Insert(-1, card)
    def Insert(self, index: int, card: 'Card', target_game_area: 'GameArea|None'=None) -> None:
        card.area = self

        if index < 0:
            index = len(self.cards) + index + 1

        if card.area == self and card in self.cards:
            self.cards.remove(card)

        self.cards.insert(index, card)

        if target_game_area:
            game_area = target_game_area
        elif self.bind_card:
            game_area = self.bind_card.GetGameArea()
        elif self.play_area:
            game_area = self.play_area.GetIdentity().card.GetGameArea()
        else:
            game_area = self.GetOwner().GetGameArea()

        if card.GetGameArea() != game_area:
            game_area.AddCard(card)
        if not self.flags.is_removed and not self.flags.is_place_card_area:
            # card.FlipTo(self.IsFaceUp(), group)
            if card.state.is_face_up != self.flags.is_face_up and card.back_faces == []:
                card.state.is_face_up = self.flags.is_face_up
    def GetSize(self) -> int:
        return len(self.cards)
    def Sort(self) -> None:
        self.cards = sorted(self.cards, reverse=True)

    def CleanAllCardsStatuesInternal(self):
        for card in self.cards:
            card.can_state.Reset()
            card.is_apply_unique_rule = None
            card.visible.Clean()

    def UpdateAllCardsStatuesInternal(self):
        for card in self.cards:
            card.visible.Update()

    def Unshuffle(self, by_effect: 'Effect'):
        self.cards = self.for_undo_shuffle[:]

    def ShuffleInternal(self, by_effect: 'Effect', only_for_most_top: int|None):
        from game.operate.rand import Rand
        from game.message import Message

        self.CleanAllCardsStatuesInternal()
        if only_for_most_top != None:
            sublist = self.cards[-only_for_most_top:]
            Rand.Shuffle(sublist, by_effect)
            self.cards[-only_for_most_top:] = sublist
        else:
            Rand.Shuffle(self.cards, by_effect)
        self.UpdateAllCardsStatuesInternal()

        message = Message.AfterDeckShuffle(self, self.bind_discard_pile)
        message.Send()

    def Shuffle(self, by_effect: 'Effect', only_for_most_top: int|None=None) -> None:
        self.for_undo_shuffle = self.cards[:]
        if len(self.cards) > 0:
            self.ShuffleInternal(by_effect, only_for_most_top)

    def ShuffleWithDiscardPile(self, penalty: bool, by_effect: 'Effect') -> None:
        from game.message import Message
        from game.operate.faces import Faces
        if self.bind_discard_pile:
            self.shuffle_with_discard_count += 1
            Faces.MoveAllTo(self.bind_discard_pile.Get(False), self, by_effect, by_shuffle=True)

            self.ShuffleInternal(by_effect, None)

            if penalty:
                assert self.bind_discard_pile
                self.process_after_shuffle(self, by_effect)
                reset_message = Message.AfterDeckReset(self)
                reset_message.Send()
        else:
            self.Shuffle(by_effect)

    def HasThisType(self, this: 'CardFace') -> int:
        count = 0
        for face in self.Get():
            if face.IsName(this.name):
                count += 1
        return count

    # def Has(self, finder: 'CardFinder') -> int:
    #     from game.operate.faces import Faces
    #     return Faces.FindCardSize(self.Get(), finder)

    # def Pop2(self, size: int, discards: 'Deck|None',
    #         process_card: Callable[['Card'], None] = lambda card: None) -> Tuple[List['Card'], bool]:
    #     if size == 0:
    #         return [], False
    #     has_shuffle = False
    #     if size <= self.GetSize():
    #         cards = self.cards[-size:]
    #     else:
    #         cards = self.cards[:]
    #         if discards:
    #             self.cards = []
    #             self.Shuffle(discards)
    #             self.cards += cards
    #             has_shuffle = True
    #             cards = self.cards[-size:]
    #     found_cards: List[Card] = []
    #     for card in cards:
    #         card.area.cards.remove(card)
    #         card.area.cards.append(card)
    #         process_card(card)
    #         found_cards = [card] + found_cards
    #     return found_cards, has_shuffle

    # TODO: rename internal
    def PopInternal(self, size: int,
                    process: Callable[['CardFace'], Any],
                    by_effect: 'Effect',
                    *,
                    continue_after_shuffle: bool,
                    ) -> List['CardFace']:
        # from game.message import Message
        assert self.flags.is_deck
        faces: List['CardFace'] = []
        left_size = size
        # last_face = None
        
        old_shuffle_with_discard_count = self.shuffle_with_discard_count

        world = self.world

        while left_size:
            if world.is_game_over:
                break
            if self.GetOwner().is_eliminated:
                break

            if self.GetSize() > 0:
                face = self.Get(True)[0]
                # See "40043"
                # assert face != last_face

                # last_face = face
                process(face)
                faces.append(face)
                left_size -= 1

            if not continue_after_shuffle:
                if self.shuffle_with_discard_count != old_shuffle_with_discard_count:
                    break

            if self.GetSize() == 0:
                break
                # message = Message.AfterDeckRunOut(self)
                # message.Send()
                # if self.bind_discard_pile and self.bind_discard_pile.GetSize() != 0:
                #     # break
                #     # # assert False
                #     # self.ShuffleWithDiscardPile(True, by_effect)
                #     # if not continue_after_shuffle:
                #     #     break
                # else:
                #     break
                # if not continue_after_shuffle:
                #     break

            if left_size == 0:
                break

        return faces

    ################################################################################
    #
    def MoveToTopAndFlip(self, card: 'Card', by_effect: 'Effect', *, ui_group: bool=False):
        card.MoveToTop(self, by_effect)
        if not card.IsFaceUp():
            card.Flip(by_effect, ui_group=ui_group)

    TCA = TypeVar("TCA", bound='CardFace')

    def FindCard(self,
                 finder: 'CardFinder|None'=None,
                 *,
                 name: str|None=None,
                 trait: "CardFace.TRAITS|None"=None,
                 card_type: 'Type[TCA]|CardFace'=CardFaceType,
                 **kwargs: Unpack['CardFinder.KWArgs'],
                 ) -> TCA|None:
        faces = self.FindCards(
            finder=finder,
            name=name,
            trait=trait,
            card_type=card_type,
            max=1,
            **kwargs,
            )
        return faces[0] if faces != [] else None

    def FindCards(self,
                finder: 'CardFinder|None'=None,
                *,
                include_removed: bool=False,
                name: str|None=None,
                trait: "CardFace.TRAITS|None"=None,
                card_type: 'Type[TCA]|CardFace'=CardFaceType,
                max: int=Math.INT_INF,
                **kwargs: Unpack['CardFinder.KWArgs'],
                ) -> List['TCA']:
        from game.operate.filter import Filter
        from game.card.card_finder import CardFinder
        # from game.card.face.card_face import CardFace

        if max == 0:
            return []
        # if card_type == 'CardFace': # type: ignore
        #     card_type = CardFace # type: ignore

        card_finder = CardFinder(
            name=name,
            trait=trait,
            card_type=card_type,
            **kwargs) & finder

        faces: List[Any] = Filter.ByFinder(
            self.GetAll(include_removed=include_removed),
            card_finder,
            max=max,
        )
        return faces

    def FindCardSizeOld(self,
                        finder: 'CardFinder',
                        ) -> int:
        from game.operate.faces import Faces
        return Faces.FindCardSizeOld(self.GetAll(), finder)

    def FindCardSize(self,
                    finder: 'CardFinder|None'=None,
                    # *,
                    # name: str|None=None,
                    # trait: "CardFace.TRAITS|None"=None,
                    # card_type: 'Type[TCA|CardFace]'=CardFaceType,
                    # **kwargs: Unpack['CardFinder.KWArgs'],
                    ) -> int:
        from game.operate.faces import Faces
        return Faces.FindCardSize(self.GetAll(), finder)
        # faces = self.FindCards(
        #     finder=finder,
        #     name=name,
        #     trait=trait,
        #     card_type=card_type,
        #     **kwargs
        # )
        # return len(faces)

    def DiscardAll(self, by_effect: 'Effect') -> int:
        from game.operate.faces import Faces
        return len(Faces.DiscardAll(self.Get(True), by_effect))

    def Get(self,
            from_top: bool=False) -> List[TC]:
        faces = self.GetAll(from_top, include_removed=False)
        return [x for x in faces if isinstance(x, self.card_type)]

    # for "27116a"
    def GetAll(self, from_top: bool=False, include_removed: bool=True) -> List['CardFace']:
        faces: List['CardFace'] = []
        if from_top:
            cards = reversed(self.cards)
        else:
            cards = self.cards
        faces = [x.face for x in cards]
        if include_removed:
            faces += [x.face for x in self.removed_cards]
        return faces

    def GetBottom(self) -> 'CardFace|None':
        if len(self.cards) > 0:
            return self.cards[0].face
        else:
            return None

    def GetTop(self) -> 'CardFace|None':
        if len(self.cards) > 0:
            return self.cards[-1].face
        else:
            return None

    def GetTops(self, size: int) -> List['CardFace']:
        faces: List['CardFace'] = []
        for card in self.cards[-size:]:
            faces.append(card.face)
        return faces

    ################################################################################
    #
    def RevealTopCard(self, to_player: 'Player', by_effect: 'Effect') -> 'CardFace|None':
        faces = self.PopInternal(
            1,
            lambda face: face.Reveal(to_player, by_effect),
            by_effect,
            continue_after_shuffle=False,
        )
        if faces:
            return faces[0]
        else:
            return None

    def DiscardCardsInternal(self, size: int, by_effect: 'Effect', *, continue_after_shuffle: bool, each_time: Callable[['CardFace'], Any]|None=None) -> List['CardFace']:
        def action(face: 'CardFace'):
            face.DiscardInternal(by_effect)
            if each_time:
                each_time(face)

        faces = self.PopInternal(
            size,
            action,
            by_effect,
            continue_after_shuffle=continue_after_shuffle,
        )

        from game.message import Message
        message = Message.AfterCardsMoved({x: self for x in faces}, by_discard=True)
        message.Send()

        return faces

    def DiscardUntil(self,
                     by_effect: 'Effect',
                    #  finder: 'CardFinder|None'=None,
                     *,
                     name: str|None,
                     trait: "CardFace.TRAITS|None",
                     card_type: 'Type[TCA]|CardFace|Literal["CardFace"]',
                     **kwargs: Unpack['CardFinder.KWArgs'],
                     ) -> Tuple['TCA|None', Sequence['CardFace']]: # `other_discard_faces`
        assert self.flags.is_deck
        from game.card.card_finder import CardFinder
        from game.card.face.card_face import CardFace

        if isinstance(card_type, CardFace):
            card_type2 = CardFace
        else:
            card_type2 = card_type

        finder = CardFinder(
            name=name,
            trait=trait,
            card_type=card_type2,
            **kwargs,
            )
        found_face = None

        other_discard_faces: List['CardFace'] = []
        old_shuffle_with_discard_count = self.shuffle_with_discard_count
        max_repeat_times = 10000
        while self.GetSize() > 0:
            assert max_repeat_times > 0, "Discard-until did not find a matching card"
            max_repeat_times -= 1
            face = self.Get(True)[0]
            face.DiscardInternal(by_effect)
            if not finder or finder.Check(face):
                found_face = face
                break
            else:
                other_discard_faces.append(face)

            # Rules Reference 1.8, Player Deck / Encounter Deck: when a
            # discard effect empties a deck, the deck resets as normal, but
            # the discard effect does not continue through the newly
            # shuffled deck.
            if self.shuffle_with_discard_count != old_shuffle_with_discard_count:
                break

        moved_faces = other_discard_faces + [found_face] if found_face else []
        from game.message import Message
        message = Message.AfterCardsMoved({x: self for x in moved_faces}, by_discard=True)
        message.Send()

        if found_face != None:
            if isinstance(card_type, CardFace) or card_type == 'CardFace':
                return Cast(Any, found_face), other_discard_faces
            else:
                assert isinstance(found_face, card_type)
                return found_face, other_discard_faces
        return None, other_discard_faces

    # def FindTopmostCard(self, card_type: 'Type[TCA]', card_finder: 'CardFinder') -> 'TCA|None':
    #     for face in self.Get(True):
    #         if card_type.IsType(face) and card_finder.Check(face):
    #             return face
    #     return None

    def FindTopmost(self, card_finder: 'CardFinder2[TCA]') -> 'TCA|None':
        for face in self.Get(True):
            if card_finder.Check(face):
                return face # type: ignore
        return None

Deck = Deck2['CardFace']
