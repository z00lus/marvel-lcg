from . import *

# Raised by the Kingpin


def GetAbilities() -> Sequence['Ability']:

    def raised_by_the_kingpin(effect: 'Effect', message: 'Message.WhenObligationGiveToPlayer') -> None:
        PutKingpinIntoPlay(effect, message.GetGaveToPlayer())

    def place_thwarted_threat(effect: 'Effect', message: 'Message.AfterSchemeRemoveThreat') -> None:
        this = effect.this.CastTo(Obligation)
        Faces.PlaceTokensOn([this], message.value, "threat", effect)
        if this.GetTokens("threat") >= 4:
            Faces.RemoveAllFromGame([this], effect)

    return [
        AbilityFactory.WhenThisObligationGiveToYou(
            raised_by_the_kingpin,
        ),
        AbilityFactory.UnitCannotTakeDamageWhile(
            AbilityType.NonKeyword,
            CardFinder(name="Kingpin"),
            conditions=[
                lambda effect, message:
                    message.by_effect.GetInitiator() == effect.this.GetControlByPlayer()
            ],
        ),
        AbilityFactory.AfterSchemeRemoveThreat(
            AbilityType.Response,
            Scheme2,
            place_thwarted_threat,
            by_thwart=True,
            conditions=[
                lambda effect, message:
                    message.by_effect.GetInitiator() == effect.this.GetControlByPlayer()
            ],
        ),
    ]
