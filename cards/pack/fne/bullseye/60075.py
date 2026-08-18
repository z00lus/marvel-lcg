from . import *


def GetAbilities() -> Sequence['Ability']:

    def revealed(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        this = effect.this.CastTo(Treachery)
        player = message.GetToPlayer()
        villain = Worlds.FindVillain(effect)
        choices: List['Ability'] = []
        if villain:
            choices.append(AbilityFactory.ForChoiceAbility(
                "Give this card to the villain as a facedown boost card",
                lambda targets: villain.GiveBoostCard(this, effect),
            ))
        choices.append(AbilityFactory.ForChoiceAbility(
            "Remove a PERSONA support you control from the game",
            lambda targets: Faces.RemoveAllFromGame(targets, effect),
        ).SetTarget(
            CardFinder2("PERSONA", Support),
            from_where=["YouControlCards"],
        ))
        player.ChooseAbilities(effect, *choices)

    def boost(effect: 'Effect', message: 'Message.WhenCardBecomeBoost') -> None:
        if message.would_atk_message:
            message.would_atk_message.GainOverKill(effect)

    return [
        AbilityFactory.WhenThisRevealed(None, revealed),
        AbilityFactory.WhenCardBecomeBoost("This", boost, during_attack=True),
    ]
