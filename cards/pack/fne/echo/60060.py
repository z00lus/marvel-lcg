from . import *

# Raised by the Kingpin


def GetAbilities() -> Sequence['Ability']:

    def is_maya_player(effect: 'Effect', message: 'Message2') -> bool:
        player = effect.this.CastTo(Obligation).GetGaveToPlayer()
        return message.by_effect.GetInitiator() == player

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
                is_maya_player,
            ],
        ),
        AbilityFactory.AfterSchemeRemoveThreat(
            AbilityType.Response,
            Scheme2,
            place_thwarted_threat,
            by_thwart=True,
            conditions=[
                is_maya_player,
            ],
        ),
    ]
