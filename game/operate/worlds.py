from typing import TypeAlias
from . import *

class Worlds:

    Character: TypeAlias = AlterEgo|Hero|Ally|Villain|Minion

    @staticmethod
    def CastGameArea(x: 'Effect|GameArea') -> 'GameArea':
        if isinstance(x, Effect):
            from game.message.message_type import TriggerPlayerMessage
            if isinstance(x, TriggerPlayerMessage):
                return x.GetToPlayer().GetIdentity().card.game_area
            else:
                return x.this.card.game_area
        # if isinstance(x, GameArea):
        #     return x
        # if x == None:
        #     world = Worlds.GetWorld()
        #     return world.GetFirstGameArea()
        return x

    @staticmethod
    def CastWorld(x: 'Effect|World') -> 'World':
        if isinstance(x, Effect):
            return x.world
        else:
            return x

    ################################################################################
    # Deck
    # This will shuffle the deck if there is not enought cards
    # Makesure you process the card, remove them from the deck
    @staticmethod
    def PopEncounterCards(size: int, process: Callable[['CardFace'], None|bool], continue_after_shuffle: bool, by_effect: 'Effect') -> List['CardFace']:
        encounter_deck = Worlds.GetEncounterDeck(by_effect)
        encounter_discard_pile = Worlds.GetEncounterDiscardPile(by_effect)
        assert encounter_discard_pile
        world = by_effect.world

        if encounter_deck.GetSize() + encounter_discard_pile.GetSize() < size:
            world.game_over.SetGameOverByRule("There were no cards in either the encounter deck or the encounter discard pile")
            return []

        return encounter_deck.PopInternal(
            size,
            process,
            by_effect,
            continue_after_shuffle=continue_after_shuffle,
        )

    @staticmethod
    def PopEncounterCard(by_effect: 'Effect') -> 'CardFace':
        encounter_deck = Worlds.GetEncounterDeck(by_effect)
        return encounter_deck.PopInternal(
            1,
            lambda face: None,
            by_effect,
            continue_after_shuffle=False,
        )[0]

    @staticmethod
    def GetEncounterDeck(by_effect: 'Effect') -> 'Deck':
        villain = Worlds.FindVillainByGameArea(by_effect.this.card.game_area)
        if villain:
            return villain.encounter_deck
        else:
            world = by_effect.world
            return world.GetScenario().encounter_deck

    @staticmethod
    def GetEncounterDecks(by_effect: 'Effect') -> List['Deck']:
        villains = Worlds.GetVillains(by_effect)
        decks: List['Deck'] = []
        for villain in villains:
            from game.player.scenario import Scenario
            controller = villain.GetControlBy()
            if Scenario.IsType(controller):
                deck = controller.encounter_deck
                decks.append(deck)
        if not villains:
            world = by_effect.world
            decks.append(world.GetScenario().encounter_deck)
        return decks

    @staticmethod
    def GetEncounterDiscardPile(by_effect: 'Effect') -> 'Deck':
        deck = Worlds.GetEncounterDeck(by_effect)
        discard_pile = deck.bind_discard_pile
        assert discard_pile
        return discard_pile

    ################################################################################
    # Scheme
    @staticmethod
    def FindMainScheme(face: 'CardFace|Effect') -> 'MainScheme|None':
        from game.message import Message
        from game.card.face.card_type import MainScheme
        from game.effect.rule import Ties

        if isinstance(face, Effect):
            face = face.this

        # face = effect.this
        game_area = face.card.game_area
        schemes = Worlds.GetMainSchemes(game_area)
        if schemes == []:
            return None
        if len(schemes) == 1:
            return schemes[0]

        ret_main_scheme = None
        if not ret_main_scheme:
            message = Message.GettingMainScheme(game_area, face)
            message.Send()
            main_scheme = message.return_value
            if main_scheme:
                ret_main_scheme = main_scheme
        if not ret_main_scheme:
            player = face.GetOwner()
            if isinstance(player, Player):
                schemes = Worlds.GetMainSchemes(game_area)
                ret_main_scheme = player.AskChooseFace(schemes, Ties("Select Main Scheme", world=face.card.world))
        if not ret_main_scheme:
            for scheme in Worlds.GetMainSchemes(game_area):
                ret_main_scheme = scheme
                break
        # assert t != None
        if MainScheme.IsType(ret_main_scheme):
            return ret_main_scheme
        else:
            return None
    @staticmethod
    def GetMainSchemes(game_area_effect: 'GameArea|Effect') -> List['MainScheme']:
        world = game_area_effect.world
        game_area = Worlds.CastGameArea(game_area_effect)
        return [x for x in world.area_schemes_main.Get() if x.card.GetGameArea() == game_area ]

    @staticmethod
    def GetOnFieldSchemes(game_area_effect: 'GameArea|Effect', finder: 'CardFinder|None'=None) -> List['MainScheme|EncounterSideScheme|PlayerSideScheme']:
        faces =  Worlds.GetMainSchemes(game_area_effect) + Worlds.GetSideSchemes(game_area_effect)
        if finder:
            faces = finder.Checks(faces)
        return faces

    @staticmethod
    def GetSideSchemes(game_area_effect: 'GameArea|Effect') -> List['EncounterSideScheme|PlayerSideScheme']:
        world = game_area_effect.world
        game_area = Worlds.CastGameArea(game_area_effect)
        return [x for x in world.area_schemes_side.Get() if x.card.GetGameArea() == game_area and (EncounterSideScheme.IsType(x) or PlayerSideScheme.IsType(x))]

    @staticmethod
    def FilterSideScheme(by_effect: 'Effect',
                            least_threat: bool=False,
                            most_threat: bool=False,
                            ) -> 'SchemeSide2|None':
        from game.operate.filter import Filter
        targets_faces = Worlds.GetAllSideSchemes(by_effect)
        return Filter.One(
            targets_faces,
            by_effect,
            least_threat=least_threat,
            most_threat=most_threat,
        )

    ################################################################################
    # FindVillain
    @staticmethod
    def GetVillainStage(by_effect: 'Effect') -> int:
        villain = Worlds.FindVillainByGameArea(by_effect.this.card.game_area)
        if villain:
            return villain.printed_stage
        else:
            return 0

    @staticmethod
    def FindVillainByGameArea(game_area: 'GameArea') -> 'Villain|None':
        world = game_area.world
        return world.GetScenario().GetVillain(game_area)

    @staticmethod
    def FindVillain(by_effect: 'Effect', name: str|None=None) -> 'Villain|None':
        if name == None:
            this = by_effect.this
            if CanAttach.IsType(this) and \
                this.refers_to_the_villain_refers_to_attached:
                return this.GetBindFace() # type: ignore
            world = by_effect.world
            return world.GetScenario().GetVillain(by_effect.this.card.game_area)
        else:
            return Worlds.FindCardOnField(
                by_effect,
                name=name,
                card_type=Villain
            )

    @staticmethod
    def GetVillains(game_area_effect: 'GameArea|Effect', finder: 'CardFinder|None'=None) -> List['Villain']:
        game_area = Worlds.CastGameArea(game_area_effect)
        world = game_area.world
        if finder:
            villains = finder.Checks(Worlds.GetAllVillains(world))
        else:
            villains = Worlds.GetAllVillains(world)

        return [x for x in villains if x.card.GetGameArea() == game_area]

    @staticmethod
    def GetOnFieldLeaders(game_area_effect: 'GameArea|Effect') -> List['Leader']:
        game_area = Worlds.CastGameArea(game_area_effect)
        world = game_area.world
        villains = Worlds.GetAllLeaders(world)
        return [x for x in villains if x.card.GetGameArea() == game_area]

    ################################################################################
    # Unit
    @staticmethod
    def GetPlayersIdentities(game_area_effect: 'GameArea|Effect', finder: 'CardFinder|None'=None) -> List['AlterEgo|Hero']:
        units: List['AlterEgo|Hero'] = []
        for player in Worlds.GetPlayers(game_area_effect):
            units.append(player.GetIdentity())
        if finder:
            return finder.Checks(units)
        else:
            return units
    @staticmethod
    def GetOnFieldAlterEgos(game_area_effect: 'GameArea|Effect') -> List['AlterEgo']:
        from game.card.face.card_type import AlterEgo
        return [x for x in Worlds.GetPlayersIdentities(game_area_effect) if AlterEgo.IsType(x)]
    @staticmethod
    def GetOnFieldHeroes(game_area_effect: 'GameArea|Effect') -> List['Hero']:
        from game.card.face.card_type import Hero
        return [x for x in Worlds.GetPlayersIdentities(game_area_effect) if Hero.IsType(x)]
    @staticmethod
    def GetOnFieldAllies(game_area_effect: 'GameArea|Effect', finder: 'CardFinder|None'=None) -> List['Ally']:
        units: List['Ally'] = []
        for player in Worlds.GetPlayers(game_area_effect):
            units += player.allies.Get()
        if finder:
            return finder.Checks(units)
        else:
            return units
    @staticmethod
    def GetOnFieldSupports(game_area_effect: 'GameArea|Effect') -> List['Support']:
        supports: List['Support'] = []
        for player in Worlds.GetPlayers(game_area_effect):
            supports += player.supports.Get()
        return supports
    @staticmethod
    def GetOnFieldEnemies(game_area_effect: 'GameArea|Effect', finder: 'CardFinder|None'=None) -> List['Minion|Villain']:
        return Worlds.GetVillains(game_area_effect, finder) + Worlds.GetOnFieldMinions(game_area_effect, finder)

    @staticmethod
    def GetOnFieldMinions(game_area_effect: 'GameArea|Effect', finder: 'CardFinder|None'=None) -> List['Minion']:
        # Fix "50156"
        faces = Worlds.GetOnFieldCards(game_area_effect)
        units = [x for x in faces if Minion.IsType(x)]
        if finder:
            return finder.Checks(units)
        else:
            return units

    @staticmethod
    def GetOnFieldEnvironment(game_area_effect: 'GameArea|Effect') -> List['Environment']:
        return [x for x in Worlds.GetOnFieldCards(game_area_effect) if Environment.IsType(x)]

    @staticmethod
    def GetOnFieldCharacters(game_area_effect: 'GameArea|Effect', finder: 'CardFinder|None'=None) -> List['Character']:
        units: List[Worlds.Character] = []
        faces = Worlds.GetOnFieldCards(game_area_effect)
        units = [x for x in faces if Unit2.IsType(x)] # type: ignore
        if finder:
            return finder.Checks(units)
        else:
            return units

    @staticmethod
    def GetOnFieldFriendlyCharacters(game_area_effect: 'GameArea|Effect', finder: 'CardFinder|None'=None) -> List['Ally|AlterEgo|Hero']:
        units: List['Ally|AlterEgo|Hero'] = []
        for player in Worlds.GetPlayers(game_area_effect):
            units += [player.GetIdentity()] + player.allies.Get()
        if finder:
            return finder.Checks(units)
        else:
            return units

    ################################################################################
    # Crisis Acceleration Hazard tAmplify
    @staticmethod
    def GetCrisisFaces(game_area_effect: 'GameArea|Effect') -> List['CanCrisis']:
        faces = Worlds.GetOnFieldCards(game_area_effect)
        return CardFinder(crisis=True).Checks2(faces, CanCrisis)
    @staticmethod
    def GetCrisisIcons(game_area_effect: 'GameArea|Effect') -> int:
        return len(Worlds.GetCrisisFaces(game_area_effect))
    @staticmethod
    def GetAccelerationIconFaces(game_area_effect: 'GameArea|Effect') -> List['HasAccelerationIcon']:
        faces = Worlds.GetOnFieldCards(game_area_effect)
        return CardFinder(acceleration_icon=True).Checks2(faces, HasAccelerationIcon)
    @staticmethod
    def GetAccelerationTokenFaces(game_area_effect: 'GameArea|Effect') -> List['CanAccelerationToken']:
        faces = Worlds.GetOnFieldCards(game_area_effect)
        return CardFinder(acceleration_token=True).Checks2(faces, CanAccelerationToken)
    @staticmethod
    def GetAccelerationIcons(game_area_effect: 'GameArea|Effect') -> int:
        value = 0
        for face in Worlds.GetAccelerationIconFaces(game_area_effect):
            value += face.acceleration_icon
        return value
    @staticmethod
    def GetHazardFaces(game_area_effect: 'GameArea|Effect') -> List['HasHazard']:
        faces = Worlds.GetOnFieldCards(game_area_effect)
        return CardFinder(hazard=True).Checks2(faces, HasHazard)
    @staticmethod
    def GetHazardIcons(game_area_effect: 'GameArea|Effect') -> int:
        value = 0
        for face in Worlds.GetHazardFaces(game_area_effect):
            value += face.hazard
        return value
    @staticmethod
    def GetAmplifyFaces(game_area_effect: 'GameArea|Effect') -> List['HasAmplify']:
        faces = Worlds.GetOnFieldCards(game_area_effect)
        return CardFinder(amplify=True).Checks2(faces, HasAmplify)
    @staticmethod
    def GetAmplifyIcons(game_area_effect: 'GameArea|Effect') -> int:
        value = 0
        for face in Worlds.GetAmplifyFaces(game_area_effect):
            value += face.amplify
        return value

    @staticmethod
    def GetIconsNum(game_area_effect: 'GameArea|Effect', names: List[Literal["Crisis", "Acceleration", "Amplify", "Hazard"]]) -> int:
        value = 0
        for name in names:
            if name == "Hazard":
                value += Worlds.GetHazardIcons(game_area_effect)
            if name == "Amplify":
                value += Worlds.GetAmplifyIcons(game_area_effect)
            if name == "Acceleration":
                value += Worlds.GetAccelerationIcons(game_area_effect)
            if name == "Crisis":
                value += Worlds.GetCrisisIcons(game_area_effect)
        return value

    ################################################################################
    # Cards
    @staticmethod
    def GetEncounterDeckCards(by_effect: 'Effect|World') -> List['CardFace']:
        world = Worlds.CastWorld(by_effect)
        faces: List['CardFace'] = []
        villains = Worlds.GetAllVillains(by_effect)
        for villain in villains:
            faces += villain.encounter_deck.Get(True)
        if villains == []:
            return world.scenario.encounter_deck.Get()
        return faces
    @staticmethod
    def GetEncounterDiscardPileCards(by_effect: 'Effect|World', finder: 'CardFinder|None'=None) -> List['CardFace']:
        world = Worlds.CastWorld(by_effect)
        faces: List['CardFace'] = []
        villains = Worlds.GetAllVillains(by_effect)
        for villain in villains:
            faces = villain.encounter_discard_pile.Get(True)
        if villains == []:
            faces = world.scenario.encounter_discard_pile.Get()
        if finder:
            return finder.Checks(faces)
        else:
            return faces
    @staticmethod
    def GetSetAsideAreaCards(by_effect: 'Effect', finder: 'CardFinder|None'=None) -> List['CardFace']:
        world = by_effect.world
        faces = world.aside_deck.Get(True) + [x for p in world.const_players for x in p.set_aside_deck.Get(True)] + [x for p in world.const_players for x in p.set_aside_nemesis_sets.Get(True)]
        if finder:
            return finder.Checks(faces)
        else:
            return faces

    @staticmethod
    # No include status card
    def GetOnFieldCards(game_area_effect: 'GameArea|Effect') -> List['CardFace']:
        # from game.card.face.card_type import Identity
        world = game_area_effect.world
        game_area = Worlds.CastGameArea(game_area_effect)

        faces: List['CardFace'] = []
        areas: List[Deck] = []

        def get_faces(*check_faces: 'CardFace') -> List['CardFace']:
            found: List['CardFace'] = []
            for x in check_faces:
                found.append(x)
                found.extend(get_faces(*x.GetInventoryDeck().GetAll()))
                found.extend(get_faces(*x.GetPlacedCardArea().GetAll()))
            return found

        for player in Worlds.GetPlayers(game_area):
            areas += [player.area_hero, player.allies, player.supports, player.engaged_minions, player.obligations_area]

        for area in [world.area_schemes_main, world.area_schemes_side, world.scenario.area_villain] + areas:
            for face in area.GetAll():
                if face.card.game_area == game_area:
                    found = get_faces(face)
                    faces.extend(found)

        # An environment in play counts as being in each player's game area,
        # including when the scenario splits players into separate areas.
        environment_areas = [world.area_environment] + [x.area_environment for x in world.const_players]
        for area in environment_areas:
            for face in area.GetAll():
                faces.extend(get_faces(face))

        faces = [x for x in faces if x.IsFaceUp()]
        return Types.RemoveDuplicates(faces)

    ################################################################################
    # Scheme / Villain
    @staticmethod
    def GetAllMainSchemes(by_effect: 'Effect|World') -> List['MainScheme']:
        world = Worlds.CastWorld(by_effect)
        return world.area_schemes_main.Get()

    @staticmethod
    def GetAllSideSchemes(by_effect: 'Effect|World') -> List['SchemeSide2']:
        world = Worlds.CastWorld(by_effect)
        return world.area_schemes_side.Get()

    @staticmethod
    def GetOnAllFieldScheme(by_effect: 'Effect|World') -> List['MainScheme|SchemeSide2']:
        return Worlds.GetAllMainSchemes(by_effect) + \
            Worlds.GetAllSideSchemes(by_effect)

    @staticmethod
    def GetAllVillains(by_effect: 'Effect|World') -> List['Villain']:
        world = Worlds.CastWorld(by_effect)
        scenario = world.GetScenario()
        return scenario.area_villain.Get()

    @staticmethod
    def GetAllLeaders(by_effect: 'Effect|World') -> List['Leader']:
        world = Worlds.CastWorld(by_effect)
        scenario = world.GetScenario()
        return [x for x in scenario.area_villain.Get() if Leader.IsType(x)]

    ################################################################################
    #
    @staticmethod
    def FindCardOnField(by_effect: 'Effect',
                        finder: 'CardFinder|None'=None,
                        *,
                        name: str|None=None,
                        trait: "CardFace.TRAITS|None"=None,
                        card_type: Type['TC']|Any|CardFace=CardFace,
                        game_area: 'GameArea|None'=None,
                        **kwargs: Unpack['CardFinder.KWArgs'],
                        ) -> TC|None:
        faces = Worlds.FindCardsOnField(
            by_effect,
            finder,
            max=1,
            name=name,
            trait=trait,
            card_type=card_type,
            game_area=game_area,
            **kwargs)
        if faces != []:
            return faces[0]
        return None

    @staticmethod
    def FindCardSizeOnField(by_effect: 'Effect',
                            finder: 'CardFinder|None'=None,
                            *,
                            name: str|None=None,
                            trait: "CardFace.TRAITS|None"=None,
                            card_type: Type['TC']|CardFace=CardFace,
                            ) -> int:
        return len(Worlds.FindCardsOnField(
            by_effect,
            finder,
            name=name,
            trait=trait,
            card_type=card_type
        ))

    @staticmethod
    def FindCardsOnField(by_effect: 'Effect',
                         finder: 'CardFinder|None'=None,
                         *,
                         max: int=Math.INT_INF,
                         name: str|None=None,
                         trait: "CardFace.TRAITS|None"=None,
                         card_type: Type['TC']|Any|CardFace=CardFace,
                         game_area: 'GameArea|None'=None,
                         **kwargs: Unpack['CardFinder.KWArgs'],
                         ) -> List['TC']:
        from game.operate.filter import Filter
        from game.operate.referential import Referential
        if game_area == None:
            game_area = by_effect.this.card.game_area

        # We should not use the `Any`
        faces: List[Any] = Worlds.GetOnFieldCards(by_effect)
        direct_finder = CardFinder(
            name=name,
            trait=trait,
            card_type=card_type,
            game_area=game_area,
            **kwargs,
        )

        find_names: List[str] = []
        for check_finder in [finder, direct_finder]:
            if check_finder:
                for find_name in check_finder.check_by_name:
                    if find_name not in find_names:
                        find_names.append(find_name)
        if find_names:
            faces = list(Referential.Filter(
                CardFinder(names=find_names),
                faces,
                by_effect,
            ))

        if finder:
            faces = list(finder.Checks(faces))

        return Filter.ByFinder(faces, direct_finder, max=max)

    ################################################################################
    #
    @staticmethod
    def DiscardEachOther(by_effect: 'Effect',
                        this: 'CardFace',
                        trait: "CardFace.TRAITS|None"=None,
                        card_type: 'Type[TC]|CardFace'=CardFace,
                        name: str|None=None,
                        ):
        from game.operate.faces import Faces

        faces: List[CardFace] = Worlds.FindCardsOnField(
            by_effect,
            card_type=card_type,
            trait=trait,
            name=name
        )
        if this in faces:
            faces.remove(this)

        Faces.DiscardAll(faces, by_effect)

    ################################################################################
    #
    @staticmethod
    def DiscardEncounterCardsUntil(by_effect: 'Effect',
                                    *,
                                    name: str|None=None,
                                    trait: "CardFace.TRAITS|None"=None,
                                    card_type: 'Type[TC]|CardFace'=CardFace,
                                    return_other_faces: List['CardFace']|None=None,
                                    **kwargs: Unpack['CardFinder.KWArgs'],
                                    ) -> 'TC|None':
        encounter_deck = Worlds.GetEncounterDeck(by_effect)
        face, other = encounter_deck.DiscardUntil(
            by_effect,
            name=name,
            trait=trait,
            card_type=card_type,
            **kwargs
        )
        if return_other_faces != None:
            return_other_faces.clear()
            return_other_faces.extend(other)
        return face

    @staticmethod
    def RevealEncounterDeckTopCard(to_player: 'Player', by_effect: 'Effect') -> 'CardFace|None':
        encounter_deck = Worlds.GetEncounterDeck(by_effect)
        return encounter_deck.RevealTopCard(to_player, by_effect)

    @staticmethod
    def DiscardEncounterCards(num: int|Literal["1*", "2*", "4*"],
                            by_effect: 'Effect',
                            *,
                            each_time: Callable[['CardFace'], Any]|None=None) -> List['CardFace']:
        deck = Worlds.GetEncounterDeck(by_effect)
        num = Worlds.ConvertPerPlayerIconToInt(num, by_effect)
        # RR 1.8 finishes the current encounter-deck effect after an empty
        # deck is reset. Discarding several cards is one such effect.
        faces = deck.DiscardCardsInternal(num, by_effect, continue_after_shuffle=True, each_time=each_time)
        return faces

    @staticmethod
    def DiscardEncounterTopCard(by_effect: 'Effect') -> 'CardFace|None':
        faces = Worlds.DiscardEncounterCards(1, by_effect)
        if faces:
            return faces[0]
        return None

    # @staticmethod
    # def GetEncounterDeckTopCards(by_effect: 'Effect') -> List['CardFace']:
    #     faces: List['CardFace'] = []
    #     for deck in Worlds.GetEncounterDecks(by_effect):
    #         face = deck.GetTop()
    #         if face:
    #             faces.append(face)
    #     return faces

    ################################################################################
    #
    @staticmethod
    def SetGameOver(player_won: bool, by_effect: 'Effect'):
        return by_effect.world.game_over.SetPlayersWon(player_won, by_effect)

    @staticmethod
    def GetFirstPlayer(by_effect: 'Effect') -> 'Player':
        world = by_effect.world
        for player in world.players:
            if not player.is_eliminated:
                return player
        # return self.GetWorld().players[0]
        if not world.is_game_over:
            assert False
        return world.players[0]

    @staticmethod
    def GetCurrentPlayer(by_effect: 'Effect') -> 'Player':
        world = by_effect.world
        return world.GetCurrentPlayer()

    @staticmethod
    def GetNextPlayer(player: 'Player', by_effect: 'Effect') -> 'Player|None':
        world = by_effect.world
        assert player in world.const_players, f"{player=} {world.const_players=}"
        index = world.const_players.index(player)
        new_list = Types.Rotate(world.players, index)
        if len(new_list) >= 2:
            return new_list[1]
        else:
            return None

    @staticmethod
    def GetPlayers(game_area_effect: 'GameArea|Effect') -> List['Player']:
        from game.operate.worlds import Worlds
        game_area = Worlds.CastGameArea(game_area_effect)
        world = game_area.world
        return [x for x in world.const_players if x.area_hero.GetSize() > 0 and x.GetIdentity().card.GetGameArea() == game_area]

    @staticmethod
    def FindPlayerByName(name: 'str', by_effect: 'Effect') -> 'Player|None':
        players = Worlds.GetPlayers(by_effect)
        for player in players:
            if player.IsName(name):
                return player
        return None

    @staticmethod
    def FindPlayer(finder: 'PlayerFinder|None', by_effect: 'Effect', *, engaged_with_fewest_minions: bool=False) -> 'Player|None':
        from game.operate.filter import Filter

        players = Worlds.GetPlayers(by_effect)
        if finder == None:
            pass
        else:
            players = [x for x in players if finder.Check(x)]

        identity = Filter.One([x.GetIdentity() for x in players], by_effect, engaged_with_fewest_minions=engaged_with_fewest_minions)

        if identity:
            return identity.GetOwnerPlayer()
        else:
            return None

    @staticmethod
    def GetPlayerById(id: int, by_effect: 'Effect') -> 'Player':
        world = by_effect.world
        for player in world.const_players:
            if player.player_id == id:
                return player
        assert False

    @staticmethod
    def ConvertPerPlayerIconToInt(value: INT_TYPE, by_effect: 'Effect') -> int:
        if isinstance(value, str):
            return int(value[:-1]) * Worlds.GetPlayerNumIcon(by_effect)
        else:
            return value

    @staticmethod
    def GetPlayerNumIcon(by_effect: 'Effect') -> int:
        world = by_effect.world
        return world.GetPlayerNumIcon()

    @staticmethod
    def GetPlayerNum(game_area_effect: 'GameArea|Effect') -> int:
        world = game_area_effect.world
        return world.GetPlayerNum()

    @staticmethod
    def IsExpert(by_effect: 'Effect') -> bool:
        return by_effect.world.scene.campaign.expert

    @staticmethod
    def IsStandard(by_effect: 'Effect') -> bool:
        return not Worlds.IsExpert(by_effect)

    @staticmethod
    def IsGameOver(by_effect: 'Effect') -> bool:
        return by_effect.world.is_game_over

    @staticmethod
    def IsCampaign(by_effect: 'Effect') -> bool:
        return by_effect.world.rule.mode_campaign.val

    @staticmethod
    def IsCampaignSelected(by_effect: 'Effect', campaign_id: str) -> bool:
        return Worlds.IsCampaign(by_effect) and \
            by_effect.world.scene.campaign.campaign_id == campaign_id

    ################################################################################
    #
    @staticmethod
    def AsideDeck(by_effect: 'Effect') -> 'Deck':
        world = by_effect.world
        return world.aside_deck

    ASIDE_DECK_NAME: TypeAlias = Literal[
        "TheCollection",
        "ShipCommand",
        "ShowDeck",
        "InfinityStone",
        "ExperimentalWeapons",
        "SideSchemeDeck",
        "BulldozerEncounter",
        "PiledriverEncounter",
        "ThunderballEncounter",
        "HoldingCell",
        "A.I.M.Envelope",
        "S.H.I.E.L.D.Envelope",
    ]

    SCENARIO_AREA_NAME: TypeAlias = Literal[
        "MissionArea"
    ]

    @staticmethod
    def ScenarioDeck(by_effect: 'Effect', deck_name: 'ASIDE_DECK_NAME') -> 'SetAsideDeck':
        world = by_effect.world
        return world.scenario_decks[deck_name]

    @staticmethod
    def ScenarioArea(by_effect: 'Effect', deck_name: 'SCENARIO_AREA_NAME') -> 'Deck':
        if deck_name == "MissionArea":
            return by_effect.world.area_mission
        raise NotImplementedError(deck_name)

    @staticmethod
    def GetScenario(by_effect: 'Effect') -> 'Scenario':
        world = by_effect.world
        return world.GetScenario()

    @staticmethod
    def MainSchemesDeck(by_effect: 'Effect') -> 'Deck':
        world = by_effect.world
        return world.main_schemes_deck

    @staticmethod
    def AsideModular(by_effect: 'Effect') -> 'Deck':
        world = by_effect.world
        return world.aside_modular

    @staticmethod
    def VictoryDisplay(by_effect: 'Effect') -> 'Deck':
        world = by_effect.world
        return world.victory_display

    @staticmethod
    def Phase(by_effect: 'Effect'):
        world = by_effect.world
        return world.phase

    @staticmethod
    def GetDefeatedVillain(by_effect: 'Effect'):
        world = by_effect.world
        return world.area_removed.FindCards(card_type=Villain)

    @staticmethod
    def GetStandardEncounterSets(by_effect: 'Effect') -> List[str]:
        standard_encounter_sets: List[str] = []
        world = by_effect.world
        for encounter_set in world.scene.campaign.encounter_sets:
            if encounter_set.startswith("standard") or \
                encounter_set.startswith("expert"):
                standard_encounter_sets.append(encounter_set)
        return standard_encounter_sets

    @staticmethod
    def GetModularSets(by_effect: 'Effect') -> List[str]:
        encounter_sets: List[str] = []
        world = by_effect.world
        for encounter_set in world.scene.campaign.encounter_sets:
            if encounter_set.startswith("standard") or \
                encounter_set.startswith("expert"):
                pass
            else:
                encounter_sets.append(encounter_set)
        return encounter_sets

    @staticmethod
    def UpdateNextCardPlayCost(player: 'Player|Literal["Any"]',
                                update_rule: int,
                                by_effect: 'Effect',
                                *,
                                update_to: bool=False,
                                finder: 'CardFinder|None'=None,
                                # condition: Callable[['CardFace'], bool] = lambda face: True,
                                in_this: Literal["Phase", "Turn"],
                                ):
        from game.message import Message
        from game.ability import Ability, AbilityType
        from game.ability.factory import AbilityFactory
        from game.operate.effects import Effects

        def check_card_type(effect: 'Effect', message: 'Message.WhenCalculateEffectCost') -> bool:
            if finder == None:
                return True
            return finder.Check(message.check_effect.this)

        def check_card_type2(effect: 'Effect', message: 'Message.WhenPlayerWouldPlayCard') -> bool:
            if finder == None:
                return True
            return finder.Check(message.play_face)

        def set_update_fixed_cost(effect: 'Effect', message: 'Message.WhenCalculateEffectCost') -> None:
            if update_to:
                assert update_rule == 0
                message.UpdateToCost("0", effect)
            else:
                message.UpdateCost(update_rule, effect)

        phase_end = in_this == "Phase"
        turn_end = in_this == "Turn"

        def check_is_player(effect: 'Effect', message: 'TriggerNonePlayerMessage'):
            return player == "Any" or player == message.to_player

        this = by_effect.this
        modify_cost_effects = this.effect.RegisterTemp(
            AbilityFactory.WhenCalculateEffectCost(
                AbilityType.Temp0,
                set_update_fixed_cost,
                conditions=[
                    check_card_type,
                    check_is_player,
                    lambda effect, message:
                        # condition(message.check_effect.this) and \
                        message.check_effect.ability.is_play,
                ]
            ),
            unregister_after_exec=False,
            until_phase_end=phase_end,
            until_turn_end=turn_end
        )

        def unregister_modify_cost_effect(effect: 'Effect', message: 'Message2'):
            Effects.UnRegister(modify_cost_effects)

        by_effect.this.effect.RegisterTemp(
            Ability(
                AbilityType.Temp0,
                Message.WhenPlayerWouldPlayCard,
                [
                    check_card_type2,
                    check_is_player,
                    # lambda effect, message:
                    #     (
                    #         # condition(message.card_face) or \
                    #         type(message) is not Message.WhenPlayerWouldPlayCard
                    #     ),
                ],
                unregister_modify_cost_effect
            ),
            unregister_after_exec=True,
            until_phase_end=phase_end,
            until_turn_end=turn_end
        )

    @staticmethod
    def GetEnemyTeam(by_effect: 'Effect') -> 'Player':
        return Worlds.GetFirstPlayer(by_effect)

    @staticmethod
    def GetEnemyLeader(by_effect: 'Effect') -> 'Leader|None':
        leader = Worlds.FindCardOnField(
            by_effect,
            card_type=Leader
        )
        return leader

    @staticmethod
    def GetYourTeam(by_effect: 'Effect') -> 'Player':
        return Worlds.GetFirstPlayer(by_effect)

    @staticmethod
    def GetYourTeamLeader(by_effect: 'Effect') -> 'Leader|None':
        return None

    @staticmethod
    def GetYourTeamSize(by_effect: 'Effect') -> int:
        return Worlds.GetPlayerNumIcon(by_effect)

    @staticmethod
    def IsCompetitiveMode(by_effect: 'Effect') -> Literal[False]:
        return False

    @staticmethod
    def IsCooperativeMode(by_effect: 'Effect') -> bool:
        return True

    Enemies = Enemies
