from core import *
from game.ability import *
from game.card.face import *
from game.player import *
from game.world import *

class PlayerSideSchemeLimit:

    def __init__(self, world: 'World') -> None:
        self.world = world

    @staticmethod
    def CountsTowardLimit(face: 'CardFace') -> bool:
        return not face.paper.IsFromSet("Next Evolution Campaign") and \
            face.paper.card_id != "61007"

    def CheckLimit(self) -> bool:
        from game.operate.faces import Faces
        from game.effect.rule import GameRule
        from game.card.card_finder import CardFinder
        from game.card.face.card_type import PlayerSideScheme
        from game.ability.factory import AbilityFactory

        world = self.world

        limit_num = (world.started_player_num+1) // 2

        max_repeat_times = 10
        while True:
            assert max_repeat_times > 0
            max_repeat_times -= 1

            if world.is_game_over:
                return False

            player = world.GetFirstPlayer()
            faces = [
                x for x in world.area_schemes_side.Get(True)
                if PlayerSideScheme.IsType(x) and
                PlayerSideSchemeLimit.CountsTowardLimit(x)
            ]
            exceed_num = len(faces) - limit_num

            rule = GameRule(player.GetIdentity())

            def action(targets: Sequence['CardFace']):
                Faces.DiscardAll(targets, rule)

            if exceed_num > 0:
                player.ChooseAbilities(
                    rule,
                    AbilityFactory.ForChoiceAbility(
                        "Player Side Scheme Limit",
                        action,
                    ).SetTarget(faces, finder=CardFinder(canbe_discard=True))
                )
            else:
                break
        return True
