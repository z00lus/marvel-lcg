from . import *


def GetAbilities() -> Sequence['Ability']:
    def open_the_dungeons(
        effect: 'Effect',
        message: 'Message.WhenSchemeBeDefeated',
    ) -> None:
        this = effect.this.CastTo(EncounterSideScheme)
        for player in Worlds.GetPlayers(effect):
            allies = Worlds.GetSetAsideAreaCards(
                effect,
                CardFinder(card_type=Ally, trait="CAPTIVE"),
            )
            ally = player.AskChooseFace(
                allies,
                effect,
                prompt="Choose a captive ally to put into play",
            )
            if ally:
                ally.PutIntoPlay(player, effect, under_control=True)

        this.card.Flip(effect)
        jormungand = this.card.face.CastTo(Attachment)
        loki = Worlds.FindVillain(effect, name="Loki")
        if loki:
            jormungand.AttachTo2(loki, effect)

    return [
        AbilityFactory.WhenSchemeBeDefeated(
            AbilityType.WhenDefeated,
            "This",
            open_the_dungeons,
        ),
    ]
