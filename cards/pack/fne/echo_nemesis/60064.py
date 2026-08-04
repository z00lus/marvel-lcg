from . import *

# Pawn of the Kingpin


def GetAbilities() -> Sequence['Ability']:

    def pawn_alter_ego(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        this = effect.this.CastTo(Treachery)
        player = message.GetToPlayer()
        kingpin = Worlds.FindCardOnField(effect, name="Kingpin", card_type=Enemy)
        if kingpin:
            kingpin.CastTo(Enemy).DoSchemes(player, effect)
        else:
            this.GainSurge(1, effect)

    def pawn_hero(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        this = effect.this.CastTo(Treachery)
        player = message.GetToPlayer()
        hero = player.GetHero()
        hero.TakeDamage(this, hero.attack, effect)

    return [
        AbilityFactory.WhenThisRevealed(
            "Alter-Ego",
            pawn_alter_ego,
        ),
        AbilityFactory.WhenThisRevealed(
            "Hero",
            pawn_hero,
        ),
    ]
