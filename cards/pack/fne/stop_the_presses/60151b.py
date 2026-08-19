from . import *


def GetAbilities() -> Sequence['Ability']:

    def undefended_attack(
        effect: 'Effect',
        message: 'Message.AfterUnitAttackUnit',
    ) -> None:
        player = message.GetToPlayer()
        supports = GetControlledDailyBugleSupports(
            effect,
            player,
            with_stamina=True,
        )

        def place_threat(targets: Sequence['CardFace']) -> None:
            this = effect.this.CastTo(MainScheme)
            this.PlaceThreatOnSchemes(
                [this],
                3 if Worlds.IsExpert(effect) else 2,
                effect,
            )

        def remove_stamina(targets: Sequence['CardFace']) -> None:
            if targets:
                RemoveStamina(targets[0].CastTo(Support), effect)

        player.ChooseAbilities(
            effect,
            AbilityFactory.ForChoiceAbility(
                "Place 3 threat here" if Worlds.IsExpert(effect)
                else "Place 2 threat here",
                place_threat,
            ),
            AbilityFactory.ForChoiceAbility(
                "Remove 1 stamina from a DAILY BUGLE support you control",
                remove_stamina,
            ).SetTarget(supports, not_move=True),
        )

    def daily_bugle_left_play(
        effect: 'Effect',
        message: 'Message.WhenCardLeavePlay',
    ) -> None:
        Worlds.SetGameOver(False, effect)

    return [
        AbilityFactory.AfterUnitAttackUnitInternal(
            AbilityType.ForcedResponse,
            Enemy,
            Identity,
            undefended_attack,
            is_undefended_attack=True,
        ),
        AbilityFactory.WhenCardLeavePlay(
            AbilityType.NonKeywordBold,
            DAILY_BUGLE_SUPPORT,
            daily_bugle_left_play,
        ),
        AbilityFactory.IfThisSchemeStageIsCompletedPlayersLoseTheGame(),
    ]
