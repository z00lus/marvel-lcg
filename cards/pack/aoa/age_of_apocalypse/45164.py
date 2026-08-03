from . import *

# Agent of Apocalypse

def GetAbilities() -> Sequence['Ability']:

    def agent_of_apocalypse_revealed(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        this = effect.this.CastTo(Minion)
        Unused(this)

        player = message.GetToPlayer()

        area = Worlds.ScenarioArea(effect, "MissionArea")

        player.ChooseAbilities(
            effect,
            AbilityFactory.ForChoiceAbility(
                "Add Agent of Apocalypse to the mission area",
                lambda targets:
                    Faces.MoveAllTo(targets, area, effect)
            ).SetTarget([this]),
            AbilityFactory.ForChoiceAbility(
                "It activates against you",
                lambda targets:
                    this.DoActivate(player, effect)
            ).SetTarget([this])
        )

    def agent_of_apocalypse_boost(effect: 'Effect', message: 'Message.WhenCardBecomeBoost') -> None:
        this = effect.this.CastTo(Minion)
        Unused(this)

        allies = Worlds.ScenarioArea(effect, "MissionArea").FindCards(card_type=Ally)
        if allies:
            player = message.GetToPlayer()
            ally = player.AskChooseFace(
                allies,
                effect,
                prompt="Choose an ally at the mission to take 1 damage",
            )
            if ally:
                ally.TakeDamage(this, 1, effect)

        message.GiveActivatingEnemyAdditionalBoostCard(1, effect)

    return [
        AbilityFactory.WhenThisRevealed(
            None,
            agent_of_apocalypse_revealed
        ),
        AbilityFactory.WhenCardBecomeBoost(
            "This",
            agent_of_apocalypse_boost
        ),
    ]
