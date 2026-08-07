from . import *

# Target Spotter

def GetAbilities() -> Sequence['Ability']:

    def target_spotter(effect: 'Effect', message: 'Message.WhenMinionWouldEngagePlayer') -> None:
        this = effect.this.CastTo(Support)
        Unused(this)

        message.SetBeInstead(effect)

        this.effect.RegisterTemp(
            AbilityFactory.EnemyCannotActivate(
                AbilityType.Temp0,
                message.minion,
            ),
            unregister_after_exec=False,
            until_phase_end=True
        )

        initiator = effect.GetInitiator()
        def action():
            message.minion.EngagePlayer(initiator, effect)
        RunAt.AfterEventEnd(effect, message, action)


    return [
        AbilityFactory.WhenMinionWouldEngagePlayer(
            AbilityType.Interrupt,
            Minion,
            None,
            target_spotter,
            # conditions=[
            #     lambda effect, message:
            #         effect.this.GetControlByPlayer() != message.would_engaged_player
            # ]
        ).SetCostFunc(CostFunc.Counter("This", 1, 'target')),
    ]
