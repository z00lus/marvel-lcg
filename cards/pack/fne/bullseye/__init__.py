from cards.pack import *


BULLSEYE = CardFinder(name="Bullseye", card_type=Villain)


def BullseyeActivationAbility() -> 'Ability':
    """Bullseye's shared star ability on all three villain stages."""

    def activate(effect: 'Effect', message: 'Message.WhenEnemyActivateAgainstYou') -> None:
        this = effect.this.CastTo(Villain)
        Unused(this)

        this.effect.RegisterTemp(
            AbilityFactory.IncreaseBoostIconsOnEncounterCard(),
            unregister_after_exec=False,
            until_event_end=message,
        )
        if isinstance(message.would_message, Message.WhenUnitWouldAttack):
            message.would_message.GainRanged(effect)

    return AbilityFactory.WhenEnemyActivateAgainstYou(
        AbilityType.ForcedInterrupt,
        "This",
        activate,
    )
