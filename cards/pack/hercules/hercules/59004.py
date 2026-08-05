from . import *


def GetAbilities() -> Sequence['Ability']:

    def protect_humanity_revealed(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        amadeus = Find.FindAndPutIntoPlay(
            effect,
            message.GetToPlayer(),
            name="Amadeus Cho",
            card_type=Ally,
        )
        if not amadeus:
            Faces.DiscardAll([effect.this], effect)

    def redirect_villain(effect: 'Effect', message: 'Message.WhenUnitWouldAttackUnit') -> None:
        this = effect.this.CastTo(Obligation)
        ally = effect.targets[0]
        assert Unit2.IsType(ally)
        message.ChangeTarget(ally, effect)

        attack_message = message.would_atk_message

        def after_attack() -> None:
            defender = attack_message.defender
            if defender and defender.IsName("Hercules", check_all_face=True):
                this.RemoveCountersInternal(1, "labor", effect, forced=True)

        RunAt.AfterEventEnd(effect, attack_message, after_attack)

    def has_controlled_ally(effect: 'Effect', message: 'Message.WhenUnitWouldAttackUnit') -> bool:
        obligation = effect.this.CastTo(Obligation)
        player = obligation.GetGaveToPlayer()
        return bool(player.GetControlAllies())

    return [
        ReturnLaborToDeckWhenItLeavesPlay(),
        AbilityFactory.WhenThisRevealed(None, protect_humanity_revealed),
        AbilityFactory.WhenUnitWouldAttackUnit(
            AbilityType.ForcedInterrupt,
            Villain,
            CardFinder(name="Hercules", card_type=Hero),
            redirect_villain,
            conditions=[has_controlled_ally],
        ).SetTarget(Ally, from_where=["YouControlCards"]),
    ]
