from core import *

from game.card.face import *
from game.card import *
from game.deck import *
from game.player import *
from game.ability import *
from game.message import *

from cards.paper import Paper
from engine.lib import Json
from engine.file import FileManager
from cards.database import CardsDB
from game.world import *

class CardFactory:

    @staticmethod
    # names ['01001', '01002']
    def GenerateCards(names: Sequence[str], deck: 'Deck|None', world: 'World', *, ui_render: bool=True) -> Sequence['Card']:
        cards: List['Card'] = []
        for name in names:
            if name != '':
                card = CardFactory.GenerateCard(name, deck, world, ui_render=ui_render)
                cards.append(card)
        return cards

    @staticmethod
    def GenerateCard(name: str, deck: 'Deck|None', world: 'World', ui_render: bool=True) -> 'Card':
        from game.card import Card

        papers = CardFactory.FindCardPapers(name)

        faces: List['CardFace'] = []

        def create_linked_faces(paper: Paper):
            card_ids = CardsDB.FindLikedPapers(paper)
            if card_ids != []:
                CardFactory.GenerateCards(card_ids, world.aside_deck, world)

        for paper in papers:
            faces.append(CardFactory.CreateFace(paper, world))
            create_linked_faces(paper)

        if deck and deck.GetOwner():
            owner = deck.GetOwner()
        else:
            owner = world.GetScenario()

        card = Card(owner, *faces, world=world)

        if not deck:
            deck = world.area_removed

        CardFactory.CardInstantiate(card, deck, owner, world)

        if ui_render and not world.is_initializing:
            Message.AfterCardsGenerated_Text(card)
        return card

    ################################################################################
    #
    @staticmethod
    def FindCardPapers(names: str) -> Sequence['Paper']:
        papers: List['Paper'] = []
        for name in names.split(','):
            papers.append(CardsDB.FindCardPaper(name))
        return papers

    ################################################################################
    #
    @staticmethod
    def CreateFace(paper: 'Paper', world: 'World') -> 'CardFace':
        from game.card.face.base import ClassCard
        from game.card.face.card_type import Ally
        from game.card.face.card_type import Hero
        from game.card.face.card_type import AlterEgo
        from game.card.face.card_type import Event
        from game.card.face.card_type import Resource

        face = paper.GetType()(paper)
        player_num = world.GetPlayerNumIcon()
        face.Initialize(player_num)
        face.ability.Add(*CardsDB.FindAbilities(paper.card_id, paper.pack, paper.set_name))
        face.ability.Add(*face.GetAbilities())

        # Check abilities
        from build import Build
        if not Build.release:
            if ClassCard.IsType(face):
                if type(face) != Resource:
                    if type(face) == Ally:
                        if face.paper.card_id in ["45031"]:
                            pass
                        else:
                            assert len(face.ability.Find(func_name="Play")) == 1, f"{face.paper.card_id=}"
                    elif type(face) == Event:
                        play_count = len(face.ability.Find(func_name="Play"))
                        if play_count == 1:
                            pass
                        elif face.paper.card_id in ["30004", "26008", "18015", "42003", "42004", "27003", "13003", "13006", "46009"]:
                            assert play_count == 2, f"{face.paper.card_id=}"
                        elif face.paper.card_id in ["09032", "09033", "09034", "09035", "09036", "60040a", "60040b", "60040c"]:
                            assert play_count == 0, f"{face.paper.card_id=}"
                        else:
                            assert False, f"{face.paper.card_id=}"
                    else:
                        assert len(face.ability.Find(func_name="Play")) == 1, f"{face.paper.card_id=}"

                if face.printed_resource_internal.val > 0:
                    if Resource.IsType(face):
                        assert len(face.ability.Find(func_name="CheckPay")) == 1, f"{face.paper.card_id=}"
                    else:
                        assert len(face.ability.Find(func_name="CheckPay")) >= 1, f"{face.paper.card_id=}"
            if Ally.IsType(face):
                assert len(face.ability.Find(func_name="ATK")) == 1, f"{face.paper.card_id=}"
                assert len(face.ability.Find(func_name="THW")) == 1, f"{face.paper.card_id=}"
                assert len(face.ability.Find(func_name="DEF")) == 1, f"{face.paper.card_id=}"
            if Hero.IsType(face):
                assert len(face.ability.Find(func_name="ATK")) == 1, f"{face.paper.card_id=}"
                assert len(face.ability.Find(func_name="THW")) == 1, f"{face.paper.card_id=}"
                assert len(face.ability.Find(func_name="DEF")) == 1, f"{face.paper.card_id=}"
                pass
            if AlterEgo.IsType(face):
                assert len(face.ability.Find(func_name="REC")) == 1, f"{face.paper.card_id=}"
            # if Enemy.IsType(face):
            #     assert len(face.FindAbility('Scheme')) == 1, f"{face.paper.card_id=}"
        return face

    @staticmethod
    def CardInstantiate(card: 'Card', area: 'Deck', owner: 'Player|Scenario', world: 'World') -> None:
        card.area = area
        card.game_area = world.GetFirstGameArea()
        card.bind_discard_pile = area.bind_discard_pile
        area.Append(card)

        CardFactory.CardRegisterEffects(card)

    @staticmethod
    def CardRegisterEffects(card: 'Card'):
        CardFactory.FaceRegisterEffects(card.face)
        for face in card.back_faces:
            CardFactory.FaceRegisterEffects(face)
        # from game.message import Message
        # message = Message.WhenCardBeCreated(card.face)
        # message.Send()

    @staticmethod
    def FaceRegisterEffects(face: 'CardFace'):
        for ability in face.ability.abilities:
            face.effect.Registers(ability)

    @staticmethod
    # return like ['01001', '01002']
    def LoadEncounterSet(encounter_set: str) -> List[str]:
        from game.scene.replay.encounter_set import EncounterSetDescriptor
        file_path = FileManager.FindJsonPath('EncounterSet', encounter_set)
        if file_path:
            return Json.LoadAs(file_path, EncounterSetDescriptor).encounters
        else:
            return []
