from . import *
from cards.pack.aos.campaign import CampaignSetup

# Zemo's Manipulations

def GetAbilities() -> Sequence['Ability']:

    def zemos_manipulations(effect: 'Effect', message: 'Message.WhenCardSetup') -> None:
        this = effect.this.CastTo(MainScheme)
        Unused(this)

        # Prepare the evidence <i>(see rulebook p. 18)</i>.

        # During setup, when you are instructed to prepare the
        # evidence:
        # » If you are not playing in campaign mode, follow the
        # steps under “Preparing the Evidence” on page 5.
        # » If you are playing in campaign mode, simply place the
        # A.I.M. and S.H.I.E.L.D. envelopes within reach.

        if Worlds.IsCampaignSelected(effect, "agents_of_shield"):
            return

        # Put each [[Board Member]] environment into play.
        # If not playing campaign mode, place 2 secret counters on each [[Board Member]] environment.

        PreparingTheEvidence(effect)

    return [
        AbilityFactory.WhenCardSetup(
            "This",
            zemos_manipulations
        ),
        *CampaignSetup(5),
    ]
