from . import *


def GetAbilities() -> Sequence['Ability']:
    def revealed(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        this = effect.this.CastTo(Treachery)
        player = message.GetToPlayer()
        discarded = player.DiscardDeckTopCards(len(player.GetControlCards()), effect)
        energy_cards = CardFinder(has_printed_res="Y").Checks(discarded)

        for card in energy_cards:
            Unused(card)
            player.ChooseAbilities(
                effect,
                AbilityFactory.ForChoiceAbility(
                    "Take 1 indirect damage",
                    lambda targets:
                        player.GetIdentity().TakeIndirectDamage(this, 1, effect),
                ),
                AbilityFactory.ForChoiceAbility(
                    "Place 1 charge counter on Electric Charge",
                    lambda targets:
                        Faces.PlaceCountersOn(
                            [charge] if (charge := FindElectricCharge(effect)) else [],
                            1,
                            'charge',
                            effect,
                        ),
                    condition=FindElectricCharge(effect) is not None,
                ),
            )

    return [
        AbilityFactory.WhenThisRevealed(None, revealed),
    ]
