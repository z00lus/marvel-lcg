from . import *
from cards.pack.mut_gen.campaign import *

# The Brotherhood Strikes! A

def GetAbilities() -> Sequence['Ability']:

    def the_brotherhood_strikes_a(effect: 'Effect', message: 'Message.WhenCardSetup') -> None:
        this = effect.this.CastTo(MainScheme)
        Unused(this)

        SetupCards.PutIntoPlay(
            effect,
            name="Save the School",
            card_type=Environment
        )

        # faces = Worlds.AsideDeck(effect).FindCards(
        #     card_type=MainScheme
        # )
        Worlds.MainSchemesDeck(effect).Shuffle(effect)

        faces = Worlds.AsideDeck(effect).FindCards(
            card_type=Villain
        )
        Rand.Shuffle(faces, effect)

        scenario = Worlds.GetScenario(effect)
        Faces.MoveAllTo(faces, scenario.villain_deck, effect)

        villain = scenario.villain_deck.Get()[0]
        villain.PutIntoPlay("FirstPlayer", effect)

    return [
        *CampaignSetup(4),
        AbilityFactory.WhenCardSetup(
            "This",
            the_brotherhood_strikes_a
        ),
        # AbilityFactory.WhenUnitBeDefeated(
        #     AbilityType.Scenario,
        #     Villain,
        #     put_villain_into_play
        # ),
    ]
