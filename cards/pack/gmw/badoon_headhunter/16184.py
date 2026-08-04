from . import *

# On the Hunt

def GetAbilities() -> Sequence['Ability']:

    def on_the_hunt_revealed(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        this = effect.this.CastTo(Treachery)
        Unused(this)

        player = message.GetToPlayer()
        identity = player.GetIdentity()

        player.ChooseAbilities(
            effect,
            AbilityFactory.ForChoiceAbility(
                "Take 2 damage",
                lambda targets:
                    identity.TakeDamage(this, 2, effect)
            ).SetTarget("YourIdentity"),
            AbilityFactory.ForChoiceAbility(
                "Discard 1 card at random from your hand",
                lambda targets:
                    player.DiscardRandomHandCards(1, effect),
                condition=player.hand_cards.GetSize() > 0,
            )
        )

    def on_the_hunt_boost(effect: 'Effect', message: 'Message.WhenCardBecomeBoost') -> None:
        this = effect.this.CastTo(Treachery)
        Unused(this)

        message.GiveBoostCardForThisActivation(Villain, 1, effect)


    return [
        AbilityFactory.WhenThisRevealed(
            None,
            on_the_hunt_revealed
        ),
        AbilityFactory.WhenCardBecomeBoost(
            "This",
            on_the_hunt_boost
        ),
    ]
