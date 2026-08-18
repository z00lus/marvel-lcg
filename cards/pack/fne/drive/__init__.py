from cards.pack import *


NO_VEHICLE_ENEMY = CardFinder(
    card_type=Enemy,
    not_with_attach=CardFinder(trait="VEHICLE", card_type=Attachment),
)


def VehicleDamageAbility(limit: int) -> 'Ability':
    def damage(effect: 'Effect', message: 'Message.WhenUnitWouldTakeDamage') -> None:
        this = effect.this.CastTo(Attachment)
        value = message.will_take_damage
        message.PreventDamage("All", effect)
        Faces.PlaceCountersOn([this], value, 'damage', effect)
        if this.GetCounters('damage') >= limit:
            Faces.DiscardAll([this], effect)

    return AbilityFactory.WhenUnitWouldTakeDamage(
        AbilityType.ForcedInterrupt,
        "AttachedEnemy",
        damage,
    )
