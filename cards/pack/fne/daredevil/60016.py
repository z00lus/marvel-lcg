from . import *

# * Sister Maggie


def GetAbilities() -> Sequence['Ability']:

    def sister_maggie(effect: 'Effect', message: 'Message.AfterUnitRecovery') -> None:
        identity = effect.GetInitiator().GetIdentity()
        status = identity.components.status.GetDeck().Get()
        face = effect.GetInitiator().MayChooseFace(status, effect, not_move=True)
        if face:
            Faces.DiscardAll([face], effect)

    return [
        AbilityFactory.CanPlayThisSupportCard(),
        *AbilityFactory.GiveKeywordToInPlayWhenApplyThis(
            CardFinder(name="Matt Murdock"),
            recover=3,
        ),
        AbilityFactory.AfterUnitRecovery(
            AbilityType.Response,
            "You",
            sister_maggie,
        ),
    ]
