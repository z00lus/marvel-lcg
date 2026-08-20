from cards.pack import *


HAMMERHEAD = CardFinder(name="Hammerhead", card_type=Villain)
MAGGIA_ENEMY = CardFinder(trait="MAGGIA", card_type=Enemy)


def HammerheadHeadbutt(damage_if_stunned: int) -> 'Ability':
    def headbutt(effect: 'Effect', message: 'Message.AfterUnitAttackUnit') -> None:
        hammerhead = effect.this.CastTo(Villain)
        for character in message.attacked_targets:
            if character.IsStunned():
                hammerhead.DealDamage([character], damage_if_stunned, effect)
            else:
                Faces.GiveStatus([character], "Stunned", effect)

    return AbilityFactory.AfterUnitAttackAndDamageUnit(
        AbilityType.ForcedResponse,
        "This",
        Friend,
        headbutt,
    )
