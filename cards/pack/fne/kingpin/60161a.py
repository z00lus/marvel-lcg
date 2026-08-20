from . import *


def GetAbilities() -> Sequence['Ability']:
    def setup(effect: 'Effect', message: 'Message.WhenCardSetup') -> None:
        def reveal_for(player: 'Player') -> None:
            minion = player.set_aside_nemesis_sets.FindCard(
                card_type=Minion,
                is_nemesis=player,
            )
            if not minion:
                FindAndRevealUnderling(effect, player)
                return

            same_title = Worlds.FindCardOnField(effect, name=minion.name)
            if same_title:
                Faces.RemoveAllFromGame([minion], effect)
                FindAndRevealUnderling(effect, player)
            else:
                minion.Reveal(player, effect)

        Players.ForEachPlayer(effect, reveal_for)

    return [AbilityFactory.WhenCardSetup("This", setup)]
