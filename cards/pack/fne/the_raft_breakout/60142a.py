from . import *


def GetAbilities() -> Sequence['Ability']:

    def setup(effect: 'Effect', message: 'Message.WhenCardSetup') -> None:
        villain = Worlds.FindVillain(effect)
        if villain:
            SetupCards.AttachTo(
                effect,
                attach_to=villain,
                name="Master Key",
                card_type=Attachment,
            )

        for player in Worlds.GetPlayers(effect):
            prisoner = Worlds.DiscardEncounterCardsUntil(
                effect,
                trait="PRISONER",
                card_type=Minion,
            )
            if prisoner:
                prisoner.Reveal(player, effect)

    return [AbilityFactory.WhenCardSetup("This", setup)]
