from . import *

# Back Alley Burglary

def GetAbilities() -> Sequence['Ability']:

    def back_alley_burglary(effect: 'Effect', message: 'Message.AfterUnitThwartScheme') -> None:
        this = effect.this.CastTo(EncounterSideScheme)
        Unused(this)

        player = message.trigger.GetControlByPlayer()

        player.ChooseAbilities(
            effect,
            AbilityFactory.ForChoiceAbilityWithCost(
                Cost("R")
            ),
            AbilityFactory.ForChoiceAbility(
                "Discard 1 random card from your hand",
                lambda targets:
                    player.DiscardRandomHandCards(1, effect),
                condition=player.hand_cards.GetSize() > 0,
            )
        )


    return [
        AbilityFactory.AfterUnitThwartScheme(
            AbilityType.ForcedResponse,
            Identity,
            "This",
            back_alley_burglary,
        ),
    ]
