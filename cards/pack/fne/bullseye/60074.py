from . import *


def GetAbilities() -> Sequence['Ability']:

    def alter_ego(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        this = effect.this.CastTo(Treachery)
        message.GetToPlayer().GetIdentity().TakeIndirectDamage(this, 2, effect)

    def hero(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        this = effect.this.CastTo(Treachery)
        player = message.GetToPlayer()
        bullseye = Worlds.FindCardOnField(effect, BULLSEYE)
        choices: List['Ability'] = []
        if bullseye:
            choices.append(AbilityFactory.ForChoiceAbility(
                "Bullseye activates against you",
                lambda targets: bullseye.DoActivate(player, effect),
            ))
        choices.append(AbilityFactory.ForChoiceAbility(
            "Remove an ally you control from the game",
            lambda targets: Faces.RemoveAllFromGame(targets, effect),
        ).SetTarget("YourAlly"))
        player.ChooseAbilities(effect, *choices)

    def boost(effect: 'Effect', message: 'Message.WhenCardBecomeBoost') -> None:
        if message.activating_enemy and BULLSEYE.Check(message.activating_enemy):
            message.GiveActivatingEnemyAdditionalBoostCard(1, effect)
            if message.would_atk_message:
                message.would_atk_message.GainPiercing(effect)

    return [
        AbilityFactory.WhenThisRevealed("Alter-Ego", alter_ego),
        AbilityFactory.WhenThisRevealed("Hero", hero),
        AbilityFactory.WhenCardBecomeBoost("This", boost),
    ]
