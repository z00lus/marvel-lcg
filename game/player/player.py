from core import *
from game.card.face import *
from game.card import *
from game.ability import *
from game.ability.condition import *
from game.ability.factory import *
from game.selector import *
from game.player import *
from game.world.game_area import *
from engine.controller import *

from game.player.model.player_ask import PlayerAsk
from game.player.model.player_cards import PlayerCards

from game.player.action.player_get import PlayerGet
from game.player.action.player_action import PlayerAction

from game.player.element.resources_pool import ResourcesPool
from game.player.element.player_flag import PlayerFlag
from game.player.element.player_phase import PlayerPhase

from game.world import *

class Player(User, PlayerAsk, PlayerCards, PlayerGet, PlayerAction, ):
    def __enter__(self):
        # assert self.world.current_player == None
        # self.world.current_player = self
        self.world.asking_player.append(self)
        return self

    def __exit__(self, *obj: object):
        # self.world.current_player = None
        self.world.asking_player.pop()
        pass

    def __init__(self, name: str, controller: 'Controller', player_id: Literal[0, 1, 2, 3], world: 'World'):
        from game.effect.rule import GameRule

        super().__init__("player", world)
        self.is_scenario = False
        self.name: str = name
        self.controller = controller
        self.player_id: Literal[0, 1, 2, 3] = player_id
        self.get_additional_from_function: Callable[['Player'], str|None]|None = None

        from game.deck import Deck2, DeckType
        from game.card.face.card_face import CardFace
        from game.card.face.card_type import Support
        from game.card.face.card_type import Ally
        from game.card.face.card_type import Minion
        from game.card.face.card_type import Obligation
        from game.card.face.card_type import AlterEgo
        from game.card.face.card_type import Hero
        from game.card.face.card_type import Environment
        from game.player.element.player_stat import PlayerStat
        from game.player.limit_monitor import AllyLimit, RestrictedLimit, TeamLimit
        from game.player.form.form import Form
        from game.player.element.player_setup import PlayerSetup

        self.set_aside_obligations: List[Card]
        self.set_aside_nemesis_sets = Deck2(world.GetScenario(), DeckType.AsideDeck, CardFace)

        self.hand_cards = Deck2(self, DeckType.HandsArea, CardFace)
        self.player_deck = Deck2(self, DeckType.PlayerDeck, CardFace)
        self.discard_pile = Deck2(self, DeckType.DiscardPile, CardFace)
        def process_after_shuffle(deck: 'Deck', by_effect: 'Effect') -> None:
            self.DealEncounterCards(1, GameRule(self.GetIdentity()))
        self.player_deck.BindDiscardPile(self.discard_pile, process_after_shuffle)

        self.supports = Deck2(self, DeckType.SupportsArea, Support) # area_supports
        self.allies = Deck2(self, DeckType.AlliesArea, Ally) # area_allies
        self.area_hero: Deck2[AlterEgo|Hero] = Deck2(self, DeckType.HeroArea, AlterEgo|Hero)

        self.engaged_minions        = Deck2(world.GetScenario(), DeckType.EngagedEnemiesArea, Minion, related_player=self)
        self.area_environment       = Deck2(world.GetScenario(), DeckType.EnvironmentArea, Environment, related_player=self)
        self.obligations_area       = Deck2(world.GetScenario(), DeckType.ObligationsArea, Obligation, related_player=self)
        self.dealt_encounter_cards  = Deck2(world.GetScenario(), DeckType.DealtEncounterCardsDeck, CardFace, related_player=self) # Wait for reveal

        # Fix "21046"
        self.area_resources = Deck2(self, DeckType.ResourcesArea, CardFace)
        self.area_processing = Deck2(self, DeckType.ProcessingArea, CardFace)

        self.stat = PlayerStat()
        self.res_pool = ResourcesPool()
        self.flag = PlayerFlag()
        self.form = Form(self)
        self.phase = PlayerPhase(self)
        self.setup = PlayerSetup(self)

        self.has_change_form = False

        self.additional_deck = Deck2(self, DeckType.AdditionalDeck, CardFace)
        self.additional_discard_pile = Deck2(self, DeckType.AdditionalDiscardPile, CardFace)
        self.additional_deck.BindDiscardPile(self.additional_discard_pile, lambda deck, effect: None)
        self.set_aside_deck = self.additional_discard_pile
        # Hero-specific decks that must remain separate from the normal player
        # deck, such as Hercules's Labor and Gift decks.
        self.special_decks: Dict[str, Deck] = {}

        self.limit_ally = AllyLimit(self, 3)
        self.limit_restricted = RestrictedLimit(self, 2)
        self.limit_team = TeamLimit(self)

        self.is_eliminated = False
        self.hero_name = ""

    def _DiscardForeignCardsForV17Elimination(self, rule: 'Effect') -> None:
        from game.card.face.attribute.has_permanent import HasPermanent
        from game.effect.rule import GameRule
        from game.operate.faces import Faces

        foreign_faces: List[CardFace] = []
        for face in (
            self.allies.GetAll() +
            self.supports.GetAll() +
            self.obligations_area.GetAll()
        ):
            if face.GetOwner() != self and face not in foreign_faces:
                foreign_faces.append(face)

        for face in foreign_faces:
            if HasPermanent.IsType(face) and face.permanent:
                # Permanent attachments are handled when their host leaves
                # play. A top-level permanent card has no host and is removed.
                Faces.RemoveAllFromGame([face], GameRule(face))
            else:
                Faces.DiscardAll([face], rule, into_area="Owner")

    def Eliminate(self, by_effect: 'Effect'):
        from game.operate.faces import Faces
        from game.operate.worlds import Worlds
        from game.effect.rule import GameRule
        from game.message import Message
        from game.card.card_finder import CardFinder
        from game.card.face.card_type import Identity

        world = self.world

        assert self.is_eliminated == False
        self.is_eliminated = True

        if not world.rule.disable_game_over:
            # We move this forward, because some effect check when card discard, e.g. 16070
            world.CheckIsAllPlayersEliminated()

            if not world.is_game_over:

                hero = self.GetIdentity()
                rule = GameRule(hero)

                next_player = Worlds.GetNextPlayer(self, by_effect)
                if next_player != None:
                    # 1. If the eliminated player has the first player token, they
                    # pass it to the next clockwise player.
                    world.UpdatePlayersOrder(by_effect)

                    # 2. If there are minions engaged with the eliminated player,
                    # each of those minions engages the next clockwise
                    # player, retaining any attachments, damage, counters,
                    # and status cards on them.
                    game_area = self.GetGameArea()
                    if next_player.GetGameArea() == world.GetFirstGameArea():
                        for face in self.GetEngagedMinions():
                            if next_player:
                                face.EngagePlayer(next_player, by_effect)
                    else:
                        # Fix Kang
                        if game_area.FindAllPlayers() == [self]:
                            schemes: List[CardFace] = []
                            main_schemes: List[CardFace] = []
                            for scheme in Worlds.GetAllMainSchemes(by_effect):
                                if scheme.card.GetGameArea() == game_area:
                                    main_schemes.append(scheme)
                            for scheme in Worlds.GetAllSideSchemes(by_effect):
                                if scheme.card.GetGameArea() == game_area:
                                    schemes.append(scheme)
                            Faces.DiscardAll(self.GetEngagedMinions(), rule)
                            Faces.DiscardAll(schemes, rule)
                            Faces.RemoveAllFromGame(main_schemes, rule)

                    # 3. If there are cards in the eliminated player’s play area
                    # that are not owned by that player, place each of those
                    # cards in its owner’s discard pile (even if that card has
                    # the permanent keyword)
                    self._DiscardForeignCardsForV17Elimination(rule)

                    # 4. Place each card owned by the eliminated player in the
                    # eliminated player’s discard pile
                    finder = CardFinder(owner=self)
                    faces: List[CardFace] = []

                    # We must use this to discard some cards attached under
                    # other cards, such as "31032".
                    faces += world.FindCardsOnField(
                        finder=finder,
                        game_area=game_area,
                    )
                    faces += Worlds.VictoryDisplay(rule).FindCards(finder)
                    faces += finder.Checks(Worlds.GetEncounterDeckCards(rule))
                    other_faces = CardFinder(non_card_type=Identity).Checks(faces)
                    Faces.DiscardAll(other_faces, rule)

                    # 5. Remove the eliminated player’s play area and each
                    # other game element within (hand, deck, discard pile,
                    # cards in play, hit point dial, etc.) from the game.

                    # Removing the identity also invokes the generic
                    # permanent-attachment reattachment rule for any foreign
                    # attachment still hosted by it.
                    Faces.RemoveAllFromGame([hero], rule)
                    Faces.DiscardAll(hero.GetInventoryDeck().Get(), rule)
                    self.dealt_encounter_cards.DiscardAll(rule)
                    self.supports.DiscardAll(rule)
                    self.allies.DiscardAll(rule)
                    self.obligations_area.DiscardAll(rule)
                    self.hand_cards.DiscardAll(rule)
                    self.player_deck.DiscardAll(rule)
                    # We do this in the front end
                    # self.discard_pile.Sort()


                world.players.remove(self)

                message = Message.WhenPlayerEliminated(self)
                message.Send()

    ################################################################################
    # Controller
    def GetController(self) -> 'Controller':
        assert self.controller != None
        return self.controller

    ################################################################################
    #
    @override
    def GetRoleCharacter(self):
        return self.GetIdentity()

    def IsHero(self) -> bool:
        from game.card.face.card_type import Hero
        hero = self.GetIdentity()
        return Hero.IsType(hero)
    def IsInHeroForm(self, trait: "CardFace.TRAITS|None"=None) -> bool:
        if not self.IsHero():
            return False
        if trait != None and not self.GetIdentity().HasTrait(trait):
            return False
        return True
    def IsAlterEgo(self) -> bool:
        from game.card.face.card_type import AlterEgo
        hero = self.GetIdentity()
        return AlterEgo.IsType(hero)

    def IsName(self, *names: str) -> bool:
        identity = self.GetIdentity()
        def is_name(name: str) -> bool:
            if name == "SP//dr" and identity.IsName("SP//dr Suit"):
                return True
            # Fix "31025"
            if name == "Peni Parker" and identity.IsName("SP//dr Suit"):
                return True
            # Fix "45075b" find "27057"
            if name == "Spider-Man - Morales" and identity.paper.card_id.startswith("27"):
                return True
            return identity.IsName(name, check_all_face=True)

        for name in names:
            if is_name(name):
                return True
        return False

    @property
    def hand_size(self) -> int:
        return self.GetIdentity().hand_size

    ################################################################################
    #
    @override
    def GetGameArea(self) -> 'GameArea':
        if self.world.is_game_started:
            return self.GetIdentity().card.GetGameArea()
        else:
            return self.world.GetFirstGameArea()

    # def AddToGameArea(self, area: 'GameArea'):
    #     area.AddPlayer(self)

    ################################################################################
    #
    @override
    def IsPlayer(self) -> bool:
        return True

    @classmethod
    def IsType(cls, user: 'User|None') -> TypeGuard['Player']:
        if user == None:
            return False
        return user.IsPlayer()

    def IsFirstPlayer(self) -> bool:
        if self.is_eliminated:
            return False
        return self == self.world.GetFirstPlayer()
