from . import *


def GetAbilities() -> Sequence['Ability']:
    def revealed(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        this = effect.this.CastTo(Treachery)
        player = message.GetToPlayer()
        energy_cards = CardFinder(has_printed_res="Y").Checks(player.hand_cards.GetAll())

        if not energy_cards:
            this.GainSurge(1, effect)
            return

        for card in list(energy_cards):
            player.ChooseAbilities(
                effect,
                AbilityFactory.ForChoiceAbility(
                    f"Discard {card.name}",
                    lambda targets, card=card:
                        Faces.DiscardAll([card], effect),
                ),
                AbilityFactory.ForChoiceAbility(
                    "Stun a character you control",
                    lambda targets:
                        Faces.GiveStatus(targets, "Stunned", effect),
                ).SetTarget("YouControlUnit", canbe_stunned=True),
            )

    return [
        AbilityFactory.WhenThisRevealed(None, revealed),
    ]
