from core import *
from game.card.face import *
from game.ability import *
from game.selector import *
from game.deck import *
from game.ability.factory import *
from game.message import *
from game.player import *

from game.element.resources import Resources

class PlayerAsk:
    def GetPlayer(self) -> 'Player':
        from game.player import Player
        return Cast(Player, self)

    def AskSpecifyResources(self, res: 'Resources') -> 'Resources':
        g = res.GetColor("G", convert_green_res=False)
        if g == 0:
            return res

        from itertools import combinations_with_replacement
        def generate_combinations(n: int):
            letters = ["R", "B", "Y"]
            # Generate combinations with replacement
            combinations = combinations_with_replacement(letters, n)
            # Convert tuples to strings and return as a list
            return ["".join(comb) for comb in combinations]

        res_text = "R" * res.r + "B" * res.b + "Y" * res.y
        res_text += self.AskChooseOneText(generate_combinations(g))
        return Resources.FromText(res_text)

    def AskChooseResourceAllocation(self, resources: 'Resources', costs: Sequence['Cost']) -> List['Resources']|None:
        allocations = Resources.FindCostAllocations(resources, costs)
        if not allocations:
            return None
        if len(allocations) == 1:
            return allocations[0]

        text_list: List[str] = []
        for allocation in allocations:
            parts = [f"card cost: {allocation[0].color_text}"]
            for index, paid in enumerate(allocation[1:], start=1):
                parts.append(f"additional cost {index}: {paid.color_text}")
            text_list.append("; ".join(parts))
        return self.AskChooseOneText(allocations, text_list)

    def MayChoosePaper(self, name_list: Sequence[str]) -> str|None:
        name_list = [f"p_{x}" for x in name_list]
        name = self.MayChooseOneText(name_list)
        if name:
            return name.lstrip('p_')
        else:
            return None

    def AskChoosePaper(self, name_list: Sequence[str]|Sequence[None]) -> str:
        name_list = [f"p_{x}" for x in name_list]
        name = self.AskChooseOneText(name_list)
        return name.lstrip('p_')

    T = TypeVar("T")
    def MayChooseOneText(self, item_list: Sequence[T], text_list: Sequence[str]|None=None) -> T|None:
        item_list2: List[Any] = list(item_list) + [None]
        if text_list:
            text_list2 = list(text_list) + ["Cancel"]
        else:
            text_list2 = None
        return self.AskChooseOneText(item_list2, text_list2)

    def AskChooseOneText(self, item_list: Sequence[T], text_list: Sequence[str]|None=None) -> T:
        from game.card.face.card_face import CardFace
        from game.effect.rule import GameRule

        abilities: List[Ability] = []
        select = item_list[0]
        player = self.GetPlayer()
        def create_ability(item: Any, text: str):
            def invoke_select():
                nonlocal select
                select = item
            ability = AbilityFactory.ForChoiceAbility(
                text,
                lambda targets:
                    invoke_select()
            )
            return ability

        for item in item_list:
            if text_list:
                text = text_list[item_list.index(item)]
            else:
                if item or item == 0: # Fix "39009"
                    if isinstance(item, CardFace):
                        text = item.name
                    else:
                        text = str(item)
                else:
                    text = 'Cancel'
            abilities.append(create_ability(item, text))

        effect = player.ChooseAbilities(
            GameRule(player.GetIdentity()),
            *abilities
        )
        assert effect
        return select

    # def NameCardType(self) -> Type[Ally|Attachment|Environment|Event|Identity|Minion|Obligation|Resource|MainScheme|SideScheme|Support|Treachery|Upgrade|Villain]:
    def DeclareCardType(self) -> Type['Ally|Hero|AlterEgo|Minion|Villain|MainScheme|EncounterSideScheme|PlayerSideScheme|Upgrade|Support|Attachment|Environment|Event|Obligation|Treachery|Resource|Evidence']:
        from game.card.face.card_type import Ally
        from game.card.face.card_type import Hero
        from game.card.face.card_type import AlterEgo
        from game.card.face.card_type import Minion
        from game.card.face.base import Villain

        from game.card.face.card_type import MainScheme
        from game.card.face.card_type import EncounterSideScheme
        from game.card.face.card_type import PlayerSideScheme

        from game.card.face.card_type import Upgrade
        from game.card.face.card_type import Support
        from game.card.face.card_type import Attachment
        from game.card.face.card_type import Environment
        from game.card.face.card_type import Event
        from game.card.face.card_type import Obligation
        from game.card.face.card_type import Treachery
        from game.card.face.card_type import Resource
        from game.card.face.card_type import Evidence

        item_list = [Hero, AlterEgo, Ally, Event, Resource, Support, Upgrade, Obligation, MainScheme, EncounterSideScheme, PlayerSideScheme, Minion, Villain, Treachery, Attachment, Environment, Evidence]
        text_list: List[str] = []
        for item in item_list:
            text_list.append(item.__name__)
        return self.AskChooseOneText(item_list, text_list)

    # [min, max]
    def DeclareNumber(self, min: int, max: int) -> int:
        return self.AskChooseOneText(list(range(min, max+1)))

    def DeclareResourceType(self, r:bool=True, b:bool=True, y:bool=True, g:bool=True) -> "Resources.RBYG":
        text: List["Resources.RBYG"] = []
        if r:
            text.append("R")
        if b:
            text.append("B")
        if y:
            text.append("Y")
        if g:
            text.append("G")
        return self.AskChooseOneText(text)

    def DeclareStatusCard(self, *, confused: bool=True, stunned: bool=True, tough: bool=True) -> 'CardFace.STATUS|None':
        from game.card.face.card_face import CardFace
        status_text: List[str] = []
        if confused:
            status_text.append("confused")
        if stunned:
            status_text.append("stunned")
        if tough:
            status_text.append("tough")
        if status_text == []:
            return None
        status = self.AskChoosePaper(status_text)
        status = status[0].upper() + status[1:]
        return Cast(CardFace.STATUS, status)

    ################################################################################
    #
    def ChooseOrder(self, faces: Sequence['TC'], *, prompt: str="") -> List['TC']:
        from game.effect.rule import GameRule

        if len(faces) == 1:
            return list(faces)

        player = self.GetPlayer()

        effect = player.ChooseAbilities(
            GameRule(player.GetIdentity()),
            AbilityFactory.ForChoiceAbility(
                prompt,
            ).SetTarget(faces, range="All"),
        )
        if not effect:
            # Game will crash here if we don't discard the ally attached by "25031"
            assert len(faces) == 0
            return []
        else:
            return effect[0].targets # type: ignore

    ################################################################################
    #
    def AskChooseSelect(self,
                        selector: 'Selector', # include range, not_move, by_search, not_shuffle
                        by_effect: 'Effect',
                        *,
                        prompt: str="",
                        forced: bool=True,
                        # peek: bool=True,
                        labels: List['Ability.LABEL']=[],
                        for_second_target: bool=False,
                        ) -> List['CardFace']:
        player = self.GetPlayer()

        # Fix "31029", "03010"
        # targets = selector.GetAllLegalTargets(by_effect)
        # range = selector.GetTargetRange(by_effect, targets)
        # if range == None:
        #     return []
        # ability = AbilityFactory.ForChoiceAbility(
        #     text,
        # ).SetLabel(*labels) \
        # .SetTargetInternal(
        #     Select.From(faces=targets,
        #                 range=range,
        #                 not_move=selector.end_process.not_move,
        #                 by_search=selector.is_search,
        #                 not_shuffle=selector.end_process.not_shuffle)
        # )

        ability = AbilityFactory.ForChoiceAbility(
            prompt,
        ).SetLabel(*labels) \
        .SetTargetInternal(
            selector
        )

        if forced:
            effects = player.ChooseAbilities(
                by_effect,
                ability,
                for_second_target=for_second_target
            )
            effect = effects[0] if effects else None
        else:
            effect = player.MayChooseOneAbility(
                by_effect,
                ability,
            )

        if effect:
            return effect.targets
        else:
            return []

    def AskChooseFaces(self,
                        faces: Sequence['TC'],
                        range: 'SELECT.RANGE_TYPE',
                        by_effect: 'Effect',
                        *,
                        prompt: str="",
                        forced: bool=True,
                        peek: bool=False,
                        not_move: bool=False,
                        not_shuffle: bool=False,
                        repeat_rules: List['SELECT.REPEAT_RULE']|'SELECT.REPEAT_RULE'=[],
                        ) -> List['TC']:
        player = self.GetPlayer()

        selector = Select.From(faces=faces,
                            range=range,
                            by_search=peek,
                            not_move=not_move,
                            not_shuffle=not_shuffle,
                            repeat_rules=repeat_rules)

        return_faces = player.AskChooseSelect(selector, by_effect, prompt=prompt, forced=forced)
        return return_faces # type: ignore

    def AskChooseFace(self,
                      faces: 'Sequence[TC]',
                      by_effect: 'Effect',
                      *,
                      prompt: str="",
                      forced: bool=True,
                      peek: bool=False,
                      not_move: bool=True,
                      ) -> 'TC|None':
        targets = self.AskChooseFaces(
            faces,
            (1, 1),
            by_effect,
            prompt=prompt,
            forced=forced,
            peek=peek,
            not_move=not_move,
        )
        if targets:
            return targets[0] # type: ignore
        return None

    def MayChooseFace(self,
                         faces: 'Sequence[TC]',
                         by_effect: 'Effect',
                         *,
                         not_move: bool=False,
                         ) -> 'TC|None':
        return self.AskChooseFace(faces, by_effect, forced=False, not_move=not_move,)

    ################################################################################
    # Discard
    def AskDiscardFaces(self, faces: Sequence['CardFace'],
                      range: 'SELECT.RANGE_TYPE|Literal["Any"]',
                      by_effect: 'Effect',
                      *,
                      not_shuffle: bool=False
                      ) -> List['CardFace']:
        from game.operate.faces import Faces
        from game.card.card_finder import CardFinder
        if range == "Any":
            range = (0, "All")
        if range == (0, 0):
            return []
        selector = Select.From(
            faces=faces,
            finder=CardFinder(canbe_discard=True),
            range=range,
            not_shuffle=not_shuffle,
            by_search=True,
            not_move=True
        )

        player = self.GetPlayer()
        # faces = player.AskChooseSelect(select, range, by_effect, not_shuffle=not_shuffle, peek=True, not_move=True)
        if by_effect.is_rule:
            text = ""
        else:
            text = "Discard"
        faces = player.AskChooseSelect(selector, by_effect, prompt=text)
        if faces:
            Faces.DiscardAll(faces, by_effect)
            return faces
        else:
            return []

    def AskDiscardFace(self, faces: Sequence['CardFace'],
                        by_effect: 'Effect',
                        *,
                        not_shuffle: bool=False
                        ) -> 'CardFace|None':
        player = self.GetPlayer()

        faces = player.AskDiscardFaces(faces, (1, 1), by_effect, not_shuffle=not_shuffle)
        assert len(faces) <= 1

        if faces:
            # Fix "16094"
            return faces[0]
        else:
            return None

    # e.g. you have only 1 cards, and need to discard at least 2
    # if forced: ("Zero", 2), you will discard all
    # if non-forced: (2, 2), you will discard []
    def DiscardHandCards(self,
                        range: 'SELECT.RANGE_TYPE',
                        # forced: bool,
                        by_effect: 'Effect',
                        *,
                        card_type: Type['CardFace']|None=None,
                        most_printed_res: bool=False,
                        highest_cost: bool=False,
                        lowest_cost: bool=False,
                        finder: 'CardFinder|None'=None,
                        ) -> List['CardFace']:
        from game.operate.filter import Filter
        player = self.GetPlayer()

        faces = player.hand_cards.Get()
        if card_type:
            faces = Filter.ByType(faces, card_type)
        if finder:
            faces = finder.Checks(faces)
        faces = Filter.All(faces, most_printed_res=most_printed_res, highest_cost=highest_cost, lowest_cost=lowest_cost)

        if len(faces) == 0:
            return []

        faces = player.AskDiscardFaces(faces,
            range,
            by_effect,
        )

        return faces

    def DiscardControlCards(self,
                            by_effect: 'Effect',
                            *,
                            ally: bool=False,
                            upgrade: bool=False,
                            support: bool=False,
                            control: bool=False, # ally + upgrade + support + player side scheme
                            # hand: bool=False, Call `AskDiscardHandCards`
                            range: 'SELECT.RANGE_TYPE'=(1,1),
                            card_type: Type['CardFace']|None=None,
                            finder: 'CardFinder|None'=None,
                            highest_cost: bool=False,
                            lowest_cost: bool=False,
                            most_printed_res: bool=False,
                            ) -> 'CardFace|None':
        from game.operate.filter import Filter
        from game.card.card_finder import CardFinder
        player = self.GetPlayer()
        player_side_scheme = False

        if control or (ally == False and upgrade == False and support == False):
            ally = True
            upgrade = True
            support = True
            player_side_scheme = True

        faces = player.GetControlCardsByType(ally=ally, upgrade=upgrade, support=support, player_side_scheme=player_side_scheme)
        # if hand:
        #     faces += player.hand_cards.Get()

        if card_type:
            faces = Filter.ByType(faces, card_type)
        if finder:
            faces = finder.Checks(faces)

        faces = CardFinder(canbe_discard=True).Checks(faces)
        faces = Filter.All(faces, highest_cost=highest_cost, lowest_cost=lowest_cost, most_printed_res=most_printed_res)
        faces = player.AskDiscardFaces(faces, range, by_effect)
        # assert len(faces) <= 1

        if faces:
            # Fix "16094"
            return faces[0]
        else:
            return None
