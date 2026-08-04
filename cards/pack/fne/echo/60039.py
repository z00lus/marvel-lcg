from . import *

# * Daredevil: Matt Murdock


def GetAbilities() -> Sequence['Ability']:

    def daredevil(effect: 'Effect', message: 'Message.AfterUnitUseBasicPower') -> None:
        this = effect.this.CastTo(Ally)
        player = effect.GetInitiator()

        cost_effects = this.effect.RegisterTemp(
            AbilityFactory.ReduceCostToPlayFaceWhen(Event, 1, player),
            unregister_after_exec=False,
        )

        def unregister_cost() -> None:
            Effects.UnRegister(cost_effects)

        this.effect.RegisterTemp(
            AbilityFactory.AfterPlayerPlayedCard(
                AbilityType.Temp0,
                player,
                Event,
                lambda effect, message: unregister_cost(),
            ),
            unregister_after_exec=True,
        )
        RunAt.RoundEnd(effect, unregister_cost)

    return [
        AbilityFactory.AfterUnitUseBasicPower(
            AbilityType.Response,
            "This",
            daredevil,
        ),
    ]
