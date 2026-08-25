from . import *


def GetAbilities() -> Sequence['Ability']:

    def snooping_around(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        this = effect.this.CastTo(Event)
        this.RemoveThreatFromSchemes(effect.targets, 4, effect)
        PlaceEvidence(2, effect)

        discarded = Worlds.DiscardEncounterTopCard(effect)
        if discarded and (Minion.IsType(discarded) or EncounterSideScheme.IsType(discarded)):
            discarded.Reveal(effect.GetInitiator(), effect)

    return [
        AbilityFactory.WhenInYourPlayTurn(
            AbilityType.AlterEgoAction,
            snooping_around,
        ).SetPlay().SetLabel("thwart").SetTarget(Scheme2),
    ]
