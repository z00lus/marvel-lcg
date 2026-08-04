from . import *

# "What Are You?"


def GetAbilities() -> Sequence['Ability']:

    def what_are_you(effect: 'Effect', message: 'Message.WhenUnitWouldBeDefeated') -> None:
        this = effect.this.CastTo(Upgrade)
        player = effect.GetInitiator()
        identity = message.trigger.CastTo(Identity)

        message.SetBeInstead(effect)
        identity.SetHealth(4, effect)
        identity.ChangeToForm(AlterEgo, effect)

        physiology = FindIonicPhysiology(effect)
        if physiology:
            slots = max(0, 3 - physiology.GetPlacedCardArea().GetSize())
            eligible = GetEnergyCardsInDiscard(effect)
            selected = player.AskChooseFaces(eligible, (0, min(slots, len(eligible))), effect)
            TuckUnderIonic(effect, selected)

        Faces.RemoveAllFromGame([this], effect)

    return [
        AbilityFactory.WhenUnitWouldBeDefeated(
            AbilityType.ForcedInterrupt,
            CardFinder(name="Wonder Man", card_type=Identity),
            what_are_you,
        ),
    ]
