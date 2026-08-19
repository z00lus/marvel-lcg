from . import *


def GetAbilities() -> Sequence['Ability']:
    def fight(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        effect.this.DealDamage(effect.targets, 2, effect)

    return [
        CommandObligationAbility(
            'Exhaust "Fight." and remove 1 command counter → deal 2 damage to a hero or ally',
            fight,
        ).SetTarget(Hero|Ally),
        PurpleManBoostAbility(),
    ]
