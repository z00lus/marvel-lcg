from . import *


def GetAbilities() -> Sequence['Ability']:
    def revealed(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        this = effect.this.CastTo(Treachery)
        player = message.GetToPlayer()

        for character in list(player.GetControlCharacters()):
            charge = FindElectricCharge(effect)
            damage = 3 if charge and charge.GetCounters('charge') else 1

            def take_damage(
                targets: Sequence['CardFace'],
                character: 'Unit2'=character,
            ) -> None:
                Unused(targets)
                current_charge = FindElectricCharge(effect)
                current_damage = 3 if current_charge and current_charge.GetCounters('charge') else 1
                character.TakeDamage(this, current_damage, effect)
                if current_charge:
                    Faces.RemoveCountersOn([current_charge], 1, 'charge', effect)

            player.ChooseAbilities(
                effect,
                AbilityFactory.ForChoiceAbility(
                    f"Exhaust {character.name}",
                    lambda targets, character=character:
                        Faces.ExhaustAll([character], effect),
                    condition=character.IsReady(),
                ),
                AbilityFactory.ForChoiceAbility(
                    f"Deal {damage} damage to {character.name}",
                    take_damage,
                ),
            )

    return [
        AbilityFactory.WhenThisRevealed(None, revealed),
    ]
