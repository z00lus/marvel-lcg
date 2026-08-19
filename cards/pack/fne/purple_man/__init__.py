from cards.pack import *


PURPLE_MAN = CardFinder(name="Purple Man", card_type=Villain)
INFLUENCED_MINION = CardFinder(trait="INFLUENCED", card_type=Minion)


def PurpleManKeywords(*, guard: int=0, patrol: int=0, villainous: int=0) -> Sequence['Ability']:
    return AbilityFactory.GiveKeywordToInPlayWhenApplyThis(
        INFLUENCED_MINION,
        guard=guard or None,
        patrol=patrol or None,
        villainous=villainous or None,
    )


def PurpleManBoostAbility() -> 'Ability':
    def boost(effect: 'Effect', message: 'Message.WhenCardBecomeBoost') -> None:
        this = effect.this
        player = message.GetToPlayer()
        message.AfterThisActivation(
            effect,
            lambda: player.DealEncounterCard(this, effect),
        )

    return AbilityFactory.WhenCardBecomeBoost("This", boost)


def CommandObligationAbility(
    name: str,
    operation: Callable[['Effect', 'Message.WhenPlayerInTurn'], None],
) -> 'Ability':
    return (
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.ForcedAction,
            operation,
        )
        .SetName(name)
        .SetCostFunc(CostFunc.Exhaust("This"))
        .SetCostFunc(CostFunc.Counter("This", 1, "command"))
    )
