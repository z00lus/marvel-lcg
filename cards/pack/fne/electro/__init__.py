from cards.pack import *


ELECTRO = CardFinder(name="Electro", card_type=Villain)
ELECTRIC_CHARGE = CardFinder(name="Electric Charge", card_type=Attachment)


def FindElectricCharge(effect: 'Effect') -> 'Attachment|None':
    return Worlds.FindCardOnField(effect, ELECTRIC_CHARGE)


def ElectroWhenRevealed(charge_counters: Literal["2*", "3*"]) -> 'Ability':
    def revealed(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        this = effect.this.CastTo(Villain)
        player = message.GetToPlayer()

        charge = Find.FindAndAttachTo(
            effect,
            this,
            who_perform=player,
            finder=ELECTRIC_CHARGE,
        )
        if charge:
            Faces.PlaceCountersOn([charge], charge_counters, 'charge', effect)

    return AbilityFactory.WhenThisRevealed(None, revealed)


def ElectroSchemeAbility(charge_counters: int) -> 'Ability':
    def after_scheme(effect: 'Effect', message: 'Message.AfterUnitSchemeEnd') -> None:
        Unused(message)
        charge = FindElectricCharge(effect)
        if charge:
            Faces.PlaceCountersOn([charge], charge_counters, 'charge', effect)

    return AbilityFactory.AfterUnitSchemeEnd(
        AbilityType.ForcedResponse,
        "This",
        after_scheme,
    )
