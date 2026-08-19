from . import *


def GetAbilities() -> Sequence['Ability']:

    def revealed(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        player = message.GetToPlayer()
        villain = Worlds.FindVillain(effect)
        villain_art = GetArtOn(villain) if villain else []

        def move_to_identity(targets: Sequence['CardFace'], paid: 'Resources') -> None:
            if targets:
                MoveArtToIdentity(effect, player, targets[0].CastTo(Attachment))

        def otherwise(targets: Sequence['CardFace']) -> None:
            MoveArtToVillain(effect, player)
            ThisCardGainSurge(effect)

        player.ChooseAbilities(
            effect,
            AbilityFactory.ForChoiceAbilityWithCost(
                Cost("RRR"),
                "Spend 3 [physical] resources and take an ART attachment",
                move_to_identity,
            ).SetTarget(villain_art),
            AbilityFactory.ForChoiceAbility(
                "Do not spend resources: return an ART attachment and gain surge",
                otherwise,
            ),
        )

    return [AbilityFactory.WhenThisRevealed(None, revealed)]
