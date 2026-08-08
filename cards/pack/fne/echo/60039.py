from . import *

# * Daredevil: Matt Murdock


def GetAbilities() -> Sequence['Ability']:

    def daredevil(effect: 'Effect', message: 'Message.AfterUnitUseBasicPower') -> None:
        this = effect.this.CastTo(Ally)
        player = effect.GetInitiator()

        cost_effects = this.effect.RegisterTemp(
            AbilityFactory.ReduceCostToPlayFaceWhen(Event, 1, player),
            unregister_after_exec=False,
            until_round_end=True,
        )

        def unregister_cost() -> None:
            active_cost_effects = [
                cost_effect for cost_effect in cost_effects
                if not cost_effect.is_unregister
            ]
            if active_cost_effects:
                Effects.UnRegister(active_cost_effects)

        this.effect.RegisterTemp(
            AbilityFactory.AfterPlayerPlayedCard(
                AbilityType.Temp0,
                player,
                Event,
                lambda effect, message: unregister_cost(),
            ),
            unregister_after_exec=True,
        )

    return [
        AbilityFactory.AfterUnitUseBasicPower(
            AbilityType.Response,
            "This",
            daredevil,
        ),
    ]
