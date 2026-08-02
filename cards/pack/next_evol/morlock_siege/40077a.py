from . import *
from cards.pack.next_evol.campaign import *

# Knock, Knock

def GetAbilities() -> Sequence['Ability']:

    def knock_knock(effect: 'Effect', message: 'Message.WhenCardSetup') -> None:
        this = effect.this.CastTo(MainScheme)
        Unused(this)

        SetupCards.Reveal(
            effect,
            name="Routed",
            card_type=Environment
        )

        faces = Worlds.AsideDeck(effect).FindCards(
            card_type=Villain
        )
        Rand.Shuffle(faces, effect)

        scenario = Worlds.GetScenario(effect)
        Faces.MoveAllTo(faces, scenario.villain_deck, effect)

        villain = scenario.villain_deck.Get()[0]
        villain.PutIntoPlay("FirstPlayer", effect)

    return [
        *CampaignSetup(1),
        AbilityFactory.WhenCardSetup(
            "This",
            knock_knock,
        ),
    ]
