from . import *

# The Accusation

def GetAbilities() -> Sequence['Ability']:

    def the_accusation_revealed(effect: 'Effect', message: 'Message.WhenCardRevealed') -> None:
        this = effect.this.CastTo(MainScheme)
        Unused(this)

        player = Worlds.GetFirstPlayer(effect)

        earned = set(CampaignLog.GetListInternal("Evidence Earned", effect)) \
            if Worlds.IsCampaignSelected(effect, "agents_of_shield") else set()
        means = player.AskChoosePaper([
            card_id for card_id in ["50185", "50186", "50187"]
            if card_id not in earned
        ])
        motive = player.AskChoosePaper([
            card_id for card_id in ["50188", "50189", "50190"]
            if card_id not in earned
        ])
        opportunity = player.AskChoosePaper([
            card_id for card_id in ["50191", "50192", "50193"]
            if card_id not in earned
        ])
        units = Worlds.FindCardsOnField(effect, names=["Chief Medical Officer", "Chief Surveillance Officer", "Chief Tactical Officer"])
        accused = player.AskChooseFace(units, effect)
        assert accused

        buff = this.GetBuff(Buff_50168a)
        buff.means = means
        buff.motive = motive
        buff.opportunity = opportunity
        buff.accused = accused

    return [
        AbilityFactory.WhenThisRevealed(
            None,
            the_accusation_revealed
        ),
    ]
