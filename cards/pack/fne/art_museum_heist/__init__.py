from cards.pack import *


ART = CardFinder(trait="ART", card_type=Attachment)


def GetArtOn(face: 'CardFace') -> List['Attachment']:
    return face.GetInventoryDeck().FindCards(ART)


def GetArtOnIdentities(effect: 'Effect') -> List['Attachment']:
    arts: List['Attachment'] = []
    for player in Worlds.GetPlayers(effect):
        arts += GetArtOn(player.GetIdentity())
    return arts


def ChooseArt(player: 'Player', arts: Sequence['Attachment'], effect: 'Effect') -> 'Attachment|None':
    if not arts:
        return None
    if len(arts) == 1:
        return arts[0]
    return player.AskChooseFace(list(arts), effect)


def MoveArtToVillain(effect: 'Effect', player: 'Player') -> bool:
    villain = Worlds.FindVillain(effect)
    art = ChooseArt(player, GetArtOnIdentities(effect), effect)
    return bool(villain and art and art.AttachTo2(villain, effect))


def MoveArtToIdentity(effect: 'Effect', player: 'Player', art: 'Attachment') -> bool:
    identities = [candidate.GetIdentity() for candidate in Worlds.GetPlayers(effect)]
    identity = identities[0] if len(identities) == 1 else player.AskChooseFace(identities, effect)
    return bool(identity and art.AttachTo2(identity, effect))


def ArtHeroAction(resource: Literal["R", "B", "Y", "G"]) -> 'Ability':
    resource_names = {
        "R": "[physical]",
        "B": "[mental]",
        "Y": "[energy]",
        "G": "[wild]",
    }

    def action(effect: 'Effect', message: 'Message.WhenPlayerInTurn') -> None:
        this = effect.this.CastTo(Attachment)
        player = message.GetToPlayer()

        def attach_to_hero() -> None:
            this.AttachTo2(player.GetHero(), effect)

        player.ChooseAbilities(
            effect,
            AbilityFactory.ForChoiceAbilityWithCost(
                Cost(resource),
                f"Spend a {resource_names[resource]} resource",
                lambda targets, paid: attach_to_hero(),
            ),
            AbilityFactory.ForChoiceAbility(
                "Exhaust your hero",
                lambda targets: attach_to_hero(),
                targets_is_exhaust_cost=True,
            ).SetCostFunc(CostFunc.Exhaust("YourHero")),
        )

    return AbilityFactory.WhenInYourPlayTurn(AbilityType.HeroAction, action)


def ArtAttachmentAbilities(
    resource: Literal["R", "B", "Y", "G"],
    status: 'CardFace.STATUS|None'=None,
    *,
    stalwart: bool=False,
) -> List['Ability']:
    abilities: List['Ability'] = [
        AbilityFactory.AttachToFaceWhenPutIntoPlay(Villain),
        ArtHeroAction(resource),
    ]

    if status:
        abilities.append(
            AbilityFactory.AfterCardAttachTo(
                AbilityType.ForcedResponse,
                "This",
                Unit2,
                lambda effect, message:
                    Faces.GiveStatus([message.to_face], status, effect),
            )
        )

    if stalwart:
        abilities += AbilityFactory.GiveKeywordToAttached(
            Unit2,
            stalwart=1,
        )

    return abilities
