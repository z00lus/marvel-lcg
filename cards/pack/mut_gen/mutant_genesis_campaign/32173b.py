from . import *


# Rescue Captives

def GetAbilities() -> Sequence['Ability']:
    def rescue_captives(effect: 'Effect', message: 'Message.AfterUnitDefeatedUnit') -> None:
        this = effect.this.CastTo(Environment)
        player = effect.GetInitiator()
        allies = this.GetPlacedCardArea().FindCards(card_type=Ally, is_face_up=False)
        ally = player.AskChooseFace(allies, effect, prompt="Choose a captive ally")
        if ally:
            ally.FlipTo(effect, face_up=True)
            ally.PutIntoPlay(player, effect, under_control=True)

    return [
        AbilityFactory.AfterUnitDefeatedUnit(
            AbilityType.Response,
            "You",
            CardFinder2("SENTINEL", Minion),
            rescue_captives,
        ).SetCost(Cost("1")),
    ]
