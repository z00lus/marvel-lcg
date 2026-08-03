from . import *
from cards.pack.aos.campaign import CampaignSetup

# Upgrading Adaptoids

def GetAbilities() -> Sequence['Ability']:

    def upgrading_adaptoids(effect: 'Effect', message: 'Message.WhenCardSetup') -> None:
        this = effect.this.CastTo(MainScheme)
        Unused(this)

        villain = Worlds.FindVillain(effect)
        assert villain
        GetHoldingCellDeck(effect).Create(effect, villain)

        faces = Worlds.GetSetAsideAreaCards(effect, CardFinder(name="Holding Cell", card_type=Environment))
        Faces.ShuffleAllTo(faces, GetHoldingCellDeck(effect).deck, effect)
        face = GetHoldingCellDeck(effect).GetTopCard()
        if face:
            face.PutIntoPlay("FirstPlayer", effect)

        if Worlds.IsExpert(effect):
            count = 2
        else:
            count = 1

        for _ in range(count):
            faces = Worlds.GetSetAsideAreaCards(
                effect,
                CardFinder2("ADAPTOID", Environment)
            )
            face = Rand.RandomChoice(faces, effect)
            face.PutIntoPlay("FirstPlayer", effect)

        def action(player: 'Player'):
            face = Search.EncounterCard(
                effect,
                player,
                include_discard_pile=False,
                name="Adaptoid",
            )
            if face:
                face.Reveal(player, effect)

        Players.ForEachPlayer(effect, action)


    return [
        AbilityFactory.WhenCardSetup(
            "This",
            upgrading_adaptoids
        ),
        *CampaignSetup(3),
    ]
