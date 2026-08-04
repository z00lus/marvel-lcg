from . import *

# Master Manipulator


def GetAbilities() -> Sequence['Ability']:

    def master_manipulator(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        PutKingpinIntoPlay(effect, message.GetToPlayer())

    def master_manipulator_boost(effect: 'Effect', message: 'Message.WhenCardBecomeBoost') -> None:
        if Worlds.FindCardOnField(effect, name="Kingpin"):
            effect.this.CastTo(EncounterSideScheme).Reveal(message.GetToPlayer(), effect)

    return [
        AbilityFactory.UnitCannotTakeDamageWhile(
            AbilityType.NonKeyword,
            CardFinder(name="Kingpin"),
        ),
        AbilityFactory.WhenThisRevealed(
            None,
            master_manipulator,
        ),
        AbilityFactory.WhenCardBecomeBoost(
            "This",
            master_manipulator_boost,
        ),
    ]
