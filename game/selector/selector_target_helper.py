from core import *
from game.ability import *
from game.card.face import *
from game.selector import *
from game.message import *

from game.operate.worlds import Worlds
from game.card.face.base import Asset2
from game.message.message_type import TargetsMessage
from game.selector import Select

def get_TeamUp(effect: 'Effect') -> Sequence['CardFace']:
    assert isinstance(effect.this, HasTeamUp), f"{effect.this=}"
    return effect.this.GetTeamUpUnits()

def get_VillainAndEngagedSamePlayerMinion(effect: 'Effect') -> Sequence['CardFace']:
    faces: List['CardFace'] = []
    for player in effect.world.const_seat_order_players:
        faces += player.engaged_minions.Get()
    # We cannot use this because of "50131b"
    # Worlds.GetOnFieldMinions(effect)
    return Worlds.GetVillains(effect) + faces

def get_VillainAndYouEngagedMinion(effect: 'Effect') -> Sequence['CardFace']:
    player = Select.GetYou(effect)
    return Worlds.GetVillains(effect) + player.engaged_minions.Get()

def get_Attached(effect: 'Effect') -> Sequence['CardFace']:
    if effect.ability.flags.is_choose_ability and \
        isinstance(effect.bind_message, Message.WhenPlayerChooseAbility):
        effect = effect.bind_message.by_effect
    assert Asset2.IsType(effect.this), f"{effect.this=}"
    return [effect.this.GetBindFace()]

def get_Initiator(effect: 'Effect') -> Sequence['CardFace']:
    return [effect.GetInitiator().GetIdentity()]

def get_This(effect: 'Effect') -> Sequence['CardFace']:
    if effect.ability.flags.is_choose_ability and \
        isinstance(effect.bind_message, Message.WhenPlayerChooseAbility):
        effect = effect.bind_message.by_effect
    return [effect.this]

def get_DefendingCharacter(effect: 'Effect') -> Sequence['CardFace']:
    found_faces: List['CardFace'] = []
    if isinstance(effect.bind_message, DefenderNoneMessage):
        if effect.bind_message.defender:
            found_faces = [effect.bind_message.defender]
    else:
        assert isinstance(effect.bind_message, Message.WhenCardBecomeBoost), f"{effect.bind_message=}"
        if isinstance(effect.bind_message.being_message, Message.WhenUnitBeingAttack):
            defender = effect.bind_message.being_message.would_atk_message.GetDefender()
            if defender:
                found_faces = [defender]
    return found_faces

def get_Attacker(effect: 'Effect') -> Sequence['CardFace']:
    def get_attacker(message: 'Message2') -> List['CardFace']:
        attackers: List[CardFace] = []
        if isinstance(message, AttackerMessageInternal) and message.attacker != None:
            attackers = [message.attacker]
        # Fix "05014" "26016"
        if isinstance(message, Message.WhenBoostCardTurnedFaceUp) and isinstance(message.being_message, Message.WhenUnitBeingAttack):
            attackers = [message.would_atk_message.attacker]
        attackers = [x for x in attackers if x.IsInPlay()]
        return attackers

    message = effect.GetBindMessage(Message2)
    if isinstance(message, Message.AfterPlayerPlayedCard):
        found_faces = get_attacker(message.on_message)
    else:
        if isinstance(message, CanBeInstead) and message.is_be_instead:
            found_faces = []
        else:
            found_faces = get_attacker(message)
    return found_faces

def get_Attacked(effect: 'Effect') -> Sequence['CardFace']:
    def get_attacked(message: 'Message2') -> Sequence['CardFace']:
        if isinstance(message, AttackerMessageInternal) and message.attacker != None:
            return message.attacked_targets
        return []

    message = effect.GetBindMessage(Message2)
    found_faces: Sequence['CardFace']
    if isinstance(message, Message.AfterPlayerPlayedCard):
        found_faces = get_attacked(message.on_message)
    else:
        if isinstance(message, CanBeInstead) and message.is_be_instead:
            found_faces = []
        else:
            found_faces = get_attacked(message)
    return found_faces

def get_DamageTarget(effect: 'Effect') -> Sequence['CardFace']:
    message = effect.GetBindMessage(Message2)
    if isinstance(message, Message.AfterUnitAttackEnd):
        return message.damaged_targets
    return []

def get_BoostForCard(effect: 'Effect') -> Sequence['CardFace']:
    assert isinstance(effect.bind_message, Message.WhenCardBecomeBoost|Message.WhenBoostCardTurnedFaceUp)
    return [effect.bind_message.being_message.by_face]

def get_Trigger(effect: 'Effect') -> Sequence['CardFace']:
    if isinstance(effect.bind_message, Message.WhenPlayerChooseAbility):
        message = effect.bind_message.by_effect.bind_message
    else:
        message = effect.bind_message

    if isinstance(message, Message.WhenPlayerInTurn):
        return [message.GetToPlayer().GetIdentity()]
    elif isinstance(message, TriggerUnitMessage|TriggerSchemeMessage|TriggerFaceMessage):
        return [message.trigger]
    elif isinstance(message, TriggerPlayerMessage):
        if message.to_player:
            return [message.to_player.GetIdentity()]
    assert False, f"{effect=}"

def get_Targets(effect: 'Effect') -> Sequence['CardFace']:
    assert isinstance(effect.bind_message, TargetsMessage)
    return effect.bind_message.targets

def get_to_player(effect: 'Effect') -> Sequence['CardFace']:
    assert isinstance(effect.bind_message, TriggerPlayerMessage)
    return [effect.bind_message.GetToPlayer().GetIdentity()]

def get_played_card(effect: 'Effect') -> Sequence['CardFace']:
    assert isinstance(effect.bind_message, Message.AfterPlayerPlayedCard)
    return [effect.bind_message.played_face]

def get_UsedToPayForThis(effect: 'Effect') -> Sequence['CardFace']:
    assert isinstance(effect.bind_message, Message.AfterPlayerPlayedCard)
    return [x.this for x in effect.bind_message.paid_res_effects]

def get_ThisAttachedHereCard(effect: 'Effect') -> Sequence['CardFace']:
    return effect.this.GetPlacedCardArea().Get()

def get_Players(effect: 'Effect') -> Sequence['CardFace']:
    return Worlds.GetPlayersIdentities(effect)

################################################################################
#
def get_OtherPlayers(effect: 'Effect') -> Sequence['CardFace']:
    return [x for x in Worlds.GetPlayersIdentities(effect) if x.GetControlBy() != Select.GetYou(effect)]

def get_FirstPlayer(effect: 'Effect') -> Sequence['CardFace']:
    return [Worlds.GetFirstPlayer(effect).GetIdentity()]

def get_YourHero(effect: 'Effect') -> Sequence['CardFace']:
    you = Select.GetYou(effect)
    return [you.GetIdentity()] if you.IsHero() else []

def get_YourIdentity(effect: 'Effect') -> Sequence['CardFace']:
    you = Select.GetYou(effect)
    return [you.GetIdentity()]

def get_YourAlterEgo(effect: 'Effect') -> Sequence['CardFace']:
    you = Select.GetYou(effect)
    return [you.GetIdentity()] if you.IsAlterEgo() else []

def get_YourSidekick(effect: 'Effect') -> Sequence['CardFace']:
    you = Select.GetYou(effect)
    return [face for face in you.allies.Get() if \
        face.GetInventoryDeck().FindCard(name="Sidekick", card_type=Upgrade) != None]

def get_YouControlUnit(effect: 'Effect') -> Sequence['CardFace']:
    you = Select.GetYou(effect)
    return you.GetControlCharacters()

def get_YouControlCards(effect: 'Effect') -> Sequence['CardFace']:
    you = Select.GetYou(effect)
    return you.GetControlCards()

def get_YourAlly(effect: 'Effect') -> Sequence['CardFace']:
    you = Select.GetYou(effect)
    return you.allies.Get()

def get_YourEngagedMinions(effect: 'Effect') -> Sequence['CardFace']:
    you = Select.GetYou(effect)
    return you.engaged_minions.Get()

def get_Hero_Ally(effect: 'Effect') -> Sequence['CardFace']:
    return Worlds.GetOnFieldAllies(effect) + Worlds.GetOnFieldHeroes(effect)

def get_Hero_Villain(effect: 'Effect') -> Sequence['CardFace']:
    return Worlds.GetAllVillains(effect) + Worlds.GetOnFieldHeroes(effect)

def get_Ally_Minion(effect: 'Effect') -> Sequence['CardFace']:
    return Worlds.GetOnFieldAllies(effect) + Worlds.GetOnFieldMinions(effect)

def get_Ally_Support(effect: 'Effect') -> Sequence['CardFace']:
    return Worlds.GetOnFieldAllies(effect) + Worlds.GetOnFieldSupports(effect)

def get_EnemyOrScheme(effect: 'Effect') -> Sequence['CardFace']:
    return Worlds.GetOnFieldEnemies(effect) + Worlds.GetOnFieldSchemes(effect)

def get_Upgrade_Support(effect: 'Effect') -> Sequence['CardFace']:
    return [x for x in Worlds.GetOnFieldCards(effect) if Upgrade.IsType(x) or Support.IsType(x)]

def get_LeaderMinion(effect: 'Effect') -> Sequence['CardFace']:
    return Worlds.GetOnFieldLeaders(effect) + Worlds.GetOnFieldMinions(effect)

def get_MainScheme(effect: 'Effect') -> Sequence['CardFace']:
    return Worlds.GetMainSchemes(effect)

def get_Villain(effect: 'Effect') -> Sequence['CardFace']:
    return Worlds.GetVillains(effect)

def get_Minion(effect: 'Effect') -> Sequence['CardFace']:
    return Worlds.GetOnFieldMinions(effect)

def get_SideScheme(effect: 'Effect') -> Sequence['CardFace']:
    return Worlds.GetSideSchemes(effect)

def get_PlayerSideScheme(effect: 'Effect') -> Sequence['CardFace']:
    return [x for x in Worlds.GetSideSchemes(effect) if PlayerSideScheme.IsType(x)]

def get_Upgrade(effect: 'Effect') -> Sequence['CardFace']:
    return [x for x in Worlds.GetOnFieldCards(effect) if Upgrade.IsType(x)]

def get_Support(effect: 'Effect') -> Sequence['CardFace']:
    return Worlds.GetOnFieldSupports(effect)

def get_Attachment(effect: 'Effect') -> Sequence['CardFace']:
    return [x for x in Worlds.GetOnFieldCards(effect) if Attachment.IsType(x)]

def get_Environment(effect: 'Effect') -> Sequence['CardFace']:
    return Worlds.GetOnFieldEnvironment(effect)

def get_Obligation(effect: 'Effect') -> Sequence['CardFace']:
    return [x for identity in Worlds.GetPlayersIdentities(effect) for x in identity.GetControlByPlayer().obligations_area.Get()]

def get_Ally(effect: 'Effect') -> Sequence['CardFace']:
    return Worlds.GetOnFieldAllies(effect)

def get_Hero(effect: 'Effect') -> Sequence['CardFace']:
    return Worlds.GetOnFieldHeroes(effect)

def get_AlterEgo(effect: 'Effect') -> Sequence['CardFace']:
    return Worlds.GetOnFieldAlterEgos(effect)

def get_StatusCard(effect: 'Effect') -> Sequence['CardFace']:
    return [x for unit in Worlds.GetOnFieldCharacters(effect) for x in unit.components.status.GetDeck().Get()]

def get_Friend(effect: 'Effect') -> Sequence['CardFace']:
    return Worlds.GetOnFieldFriendlyCharacters(effect)

def get_Scheme2(effect: 'Effect') -> Sequence['CardFace']:
    return Worlds.GetOnFieldSchemes(effect)

def get_Identity(effect: 'Effect') -> Sequence['CardFace']:
    return Worlds.GetPlayersIdentities(effect)

def get_EnemyLeader(effect: 'Effect') -> Sequence['CardFace']:
    leader = Worlds.GetEnemyLeader(effect)
    return [leader] if leader else []

def get_YourLeader(effect: 'Effect') -> Sequence['CardFace']:
    leader = Worlds.GetYourTeamLeader(effect)
    return [leader] if leader else []

def get_YourSuitFormUpgrade(effect: 'Effect') -> Sequence['CardFace']:
    you = Select.GetYou(effect)
    return you.GetControlUpgrade(CardFinder(card_type=Upgrade, form="Suit"))

def get_TuckHereCard(effect: 'Effect') -> Sequence['CardFace']:
    return effect.this.GetPlacedCardArea().GetAll()

def get_TuckUnderYourIdentityCard(effect: 'Effect') -> Sequence['CardFace']:
    you = Select.GetYou(effect)
    return you.GetIdentity().GetPlacedCardArea().GetAll()

def get_YourHeroTough(effect: 'Effect') -> Sequence['CardFace']:
    you = Select.GetYou(effect)
    if you.IsHero():
        return you.GetIdentity().components.status.GetDeck().FindCards(name="Tough")
    return []

def get_YourHandCards(effect: 'Effect') -> Sequence['CardFace']:
    you = Select.GetYou(effect)
    return you.hand_cards.Get()

def get_YourLikeHandCards(effect: 'Effect') -> Sequence['CardFace']:
    you = Select.GetYou(effect)
    faces = you.hand_cards.Get()
    for face in you.discard_pile.GetAll():
        if face.IsLikeInHand():
            faces.append(face)
    for face in you.player_deck.GetAll():
        if face.IsLikeInHand():
            faces.append(face)
    return faces

TARGET_MAP_FUNC: Dict['SELECT.TARGET_TYPE|CardFinderHelper.FINDER_TARGET|SELECT.TARGET_TYPE_HELPER', Callable[['Effect'], Sequence['CardFace']]] = {
    "TeamUp"                            : get_TeamUp,
    "VillainAndEngagedSamePlayerMinion" : get_VillainAndEngagedSamePlayerMinion,
    "VillainAndYouEngagedMinion"        : get_VillainAndYouEngagedMinion,
    "Attached"                          : get_Attached,
    "Initiator"                         : get_Initiator,
    "This"                              : get_This,
    "DefendingCharacter"                : get_DefendingCharacter,
    "Attacker"                          : get_Attacker,
    "Attacked"                          : get_Attacked,
    "DamageTarget"                      : get_DamageTarget,
    "BoostForCard"                      : get_BoostForCard,
    "Trigger"                           : get_Trigger,
    "Targets"                           : get_Targets,
    "ToPlayer"                          : get_to_player,
    "PlayedCard"                        : get_played_card,
    "UsedToPayForThis"                  : get_UsedToPayForThis,
    "ThisAttachedHereCard"              : get_ThisAttachedHereCard,
    "Players"                           : get_Players,
    "OtherPlayers"                      : get_OtherPlayers,
    "FirstPlayer"                       : get_FirstPlayer,
    "YourHero"                          : get_YourHero,
    "YourIdentity"                      : get_YourIdentity,
    "YourAlterEgo"                      : get_YourAlterEgo,
    "YourSidekick"                      : get_YourSidekick,
    "YouControlUnit"                    : get_YouControlUnit,
    "YouControlCards"                   : get_YouControlCards,
    "YourAlly"                          : get_YourAlly,
    "YourEngagedMinions"                : get_YourEngagedMinions,
    "Hero|Ally"                         : get_Hero_Ally,
    "Hero|Villain"                      : get_Hero_Villain,
    "Ally|Minion"                       : get_Ally_Minion,
    "Ally|Support"                      : get_Ally_Support,
    "Enemy|Scheme"                      : get_EnemyOrScheme,
    "Upgrade|Support"                   : get_Upgrade_Support,
    "Leader|Minion"                     : get_LeaderMinion,
    "YourSuitFormUpgrade"               : get_YourSuitFormUpgrade,
    "TuckHereCard"                      : get_TuckHereCard,
    "TuckUnderYourIdentityCard"         : get_TuckUnderYourIdentityCard,
    "YourHeroTough"                     : get_YourHeroTough,
    "YourHandCards"                     : get_YourHandCards,
    "YourLikeHandCards"                 : get_YourLikeHandCards,
    "Minion"                            : get_Minion,
    "Villain"                           : get_Villain,
    "EncounterSideScheme"               : get_SideScheme,
    "MainScheme"                        : get_MainScheme,
    "PlayerSideScheme"                  : get_PlayerSideScheme,
    "Upgrade"                           : get_Upgrade,
    "Support"                           : get_Support,
    "Attachment"                        : get_Attachment,
    "Environment"                       : get_Environment,
    "Obligation"                        : get_Obligation,
    "Ally"                              : get_Ally,
    "Hero"                              : get_Hero,
    "AlterEgo"                          : get_AlterEgo,
    "StatusCard"                        : get_StatusCard,
    "Friend"                            : get_Friend,
    "Scheme2"                           : get_Scheme2,
    "Identity"                          : get_Identity,
    "EnemyLeader"                       : get_EnemyLeader,
    "YourLeader"                        : get_YourLeader,
}
