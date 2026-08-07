import { Button } from "./buttons.js"
import { Cards } from "./cards.js"
import { ClassName } from "./class_name.js"
import { HoverCard } from "./hover.js"
import { Lib } from "./lib.js"
import { MoveCard } from "./move-card.js"
import { ButtonSetting, Setting } from "./settings.js"
import { UI } from "./ui.js"

const EVENT_ANIMATION: Record<string, string> = {
    // "WhenResolveSpecialAbility": "target_ability",
    // "WhenCardWouldReveal": "target2",
    // "WhenPlayerDealEncounterCard": "target2", // UI too weird
    // "WhenCardWouldMoveToArea": "reveal",
    // "WhenCardRevealed": "reveal",
    // "WhenCardEnterPlay": "reveal",
    // "AfterCardBeSpendAsResource": "reveal",
    // "LookAt_Text": "peek",
    "WhenSchemeWouldRemoveThreat"           : "thwart",
    "AfterCardRemovedToken"                 : "shock",
    "AfterUnitLossHealth"                   : "damage",
    "WhenSchemeWouldPlaceThreat"            : "scheme",
    "WhenUnitWouldTakeDamage"               : "attack", // will take damage from
    "WhenDamageIsZero_Text"                 : "attack",
    "AfterUnitGainStatus"                   : "gain_status",
    "AfterUnitLostStatus"                   : "gain_status",
    "CalcMainSchemeEscalation"              : "target", // A <- B ...
    "WhenMinionEngagePlayer"                : "target_engaged",
    "WhenCardWouldBePlacedCounter"          : "target",
    "AfterDamageBePrevented"                : "target",
    "WhenAttackGainKeyword"                 : "target",
    "IconsActivate_Text"                    : "target",
    "WhenUnitHealHealth"                    : "target_health",
    "AfterCardGainTrait"                    : "target_trait",
    "AfterCardUnApply_Text"                 : "target_apply",
    "EffectActivateTo_Text"                 : "target2", // A -> B ...
    "WhenEnemyActivateAgainstYou"           : "target2_activate",
    "WhenCardWouldGainBoostIcons_Text"      : "target2_boost",
    "WhenUnitWouldAttack"                   : "target2_attack",
    "WhenEffectWouldResolve"                : "target2_ability",
    "WhenSurgeWouldBeResolved"              : "target2_surge",
    "AfterCardLoseTrait"                    : "target2_trait",
    "WhenUnitWouldThwart"                   : "target2_thwart",
    "WhenUnitWouldScheme"                   : "target2_thwart",
    "AfterCardApply_Text"                   : "target2_apply",
    "WhenPlayerRevealCard"                  : "target2_reveal", // Game start will reveal some cards that isn't in the dealt encounter card area
    "AfterCardsExhaust_Text"                : "target3", // A, ... <- Z
    "AfterCardsReadied_Text"                : "target3",
    "AfterPlayerDealEncounterCard"          : "dealt_encounter_card",
    "EffectActivate_Text"                   : "activate",
    "AfterCardsMovedToRevealingArea_Text"   : "center_flip",
    "AfterCardsMovedToBoostingArea_Text"    : "center_flip",
    "AfterCardsGenerated_Text"              : "center_flip",
    "AfterCardFlip"                         : "target_activate", // "53001a"
    "AfterCardDiscard"                      : "target_activate",
};

type TIME_NAME = 'shock' | 'damage' | 'damage2' | 'shuffle' | 'flip' | 'status' | 'dealt' | 'reveal' | 'peek' | 'ability' | 'attack' | 'attack2' | 'target' | 'activate' | 'activate_area'|'activate_facedown'

const TIME_OUT: Record<TIME_NAME, number> = {
    'shock'     : 500,
    'damage'    : 500,
    'damage2'   : 1000,
    'shuffle'   : 1000,
    'flip'      : 1000,
    'status'    : 1000,
    'dealt'     : 2500,
    'reveal'    : 100,
    'peek'      : 4000,
    'ability'   : 1000,
    'attack'    : 1500,
    'attack2'   : 3000,
    'target'    : 1500,
    'activate'  : 1500,
    'activate_area': 100,
    'activate_facedown': 1500,
}

const dealt_encounter_card = 'dealt-encounter-card'

export class CardAnimation
{
    static animation_name = ""
    static active_card_object_ids: number[] = []
    
    private static has_anime = 0
    private static timer_objects: Record<number, HTMLElement[]> = {}
    private static has_max_anime_time = 0 // just a number
    private static anime_start_time = 240

    static reset() {
        CardAnimation.clearAttackTarget()
        CardAnimation.animation_name = ""
        CardAnimation.has_anime = 0
        CardAnimation.active_card_object_ids = []
    }

    static cleanEvent() {
        CardAnimation.clearAttackTarget()
        CardAnimation.animation_name = ""
    }

    private static clearAttackTarget() {
        document.querySelectorAll<HTMLElement>(`.card.${ClassName.attack_target}`).forEach(card_div => {
            card_div.classList.remove(ClassName.attack_target)
        })
    }

    static setEvent(event_name: string, prompt_text: string) {
        CardAnimation.clearAttackTarget()

        if( event_name == "WhenUnitBeingAttack" ) {
            CardAnimation.animation_name = "being_attacked"
        }
        else if (EVENT_ANIMATION[event_name]) {
            CardAnimation.animation_name = EVENT_ANIMATION[event_name];
        }
        else
        if ( ['WhenCardWouldUpdateKeyword_Text'].includes(event_name) ) {
            const texts = prompt_text.split(' ')
            if( texts[texts.length - 1] != "MAXHP" ) {
                CardAnimation.animation_name = "target" + 
                    (Number(texts[texts.length - 2]) > 0 ? '_' : '2_') +
                    texts[texts.length - 1].toLowerCase();
            }
        }
        else {
            CardAnimation.animation_name = ""
        }
    }

    static setAnimeTimeInit() {
        CardAnimation.has_max_anime_time = 240
        CardAnimation.anime_start_time = Date.now();
    }

    static rest_anime_time() { // ms
        const ms = UI.anime_time * CardAnimation.has_max_anime_time;
        const elapsedTime = Date.now() - CardAnimation.anime_start_time;

        if (elapsedTime > ms) {
            return 0;
        } else {
            return ms - elapsedTime;
        }
    }

    static setAnimeTimeEnd() {
        console.log( "CardAnimation.has:", CardAnimation.has_anime, CardAnimation.has_max_anime_time )
    }

    static setAnimeTime(name: TIME_NAME, call: Function|null=null) {
        // console.log("SetAnimeTime", x);
        const timeout = TIME_OUT[name]
        console.log(`Anime: ${UI.event_name} ${name} ${timeout}`)

        if( CardAnimation.has_max_anime_time <= timeout ) {
            CardAnimation.has_max_anime_time = timeout
        }

        CardAnimation.has_anime += 1
        return setTimeout(function() {
            CardAnimation.has_anime -= 1
            if( call ) {
                call()
            }
        }, UI.anime_time * timeout);
    }

    static setAnimeTime2(x: number) {
        x /= UI.anime_time
        // console.log("SetAnimeTime", x);
        if( CardAnimation.has_max_anime_time <= x ) {
            CardAnimation.has_max_anime_time = x
        }
    }

    static pause() {
        for( const key in CardAnimation.timer_objects ) {
            const timer = Number(key)
            clearInterval(timer)
        }
    }
    
    static unpause() {
        for( const key in CardAnimation.timer_objects ) {
            const timer = Number(key)
            for( const div of CardAnimation.timer_objects[timer] ) {
                div.classList.remove(
                    ClassName.look_at_card,
                    // ClassName.card_moving,
                    // ClassName.active_card,
                    // ClassName.card_shuffle,
                )
            }
        }
        CardAnimation.timer_objects = {}
    }

    ////////////////////////////////////////////////////////////////////////////////
    //
    static showEvent() {
        if( CardAnimation.animation_name == '' ) {
            return
        }
        const active_card_object_ids = CardAnimation.active_card_object_ids
        if( active_card_object_ids.length == 0 ) {
            return
        }

        function animation_shock(card_div: HTMLElement) {
            let class_name = 'animation-shock'
            card_div.querySelector('.face')!.classList.add(class_name)
            
            CardAnimation.setAnimeTime('shock', () => {
                card_div.querySelector('.face')!.classList.remove(class_name)
            })
        }
        function animation_damage(card_div: HTMLElement) {
            let class_name = 'animation-shock'
            let class_name2 = 'do-damage'
            
            card_div.querySelector('.face')!.classList.add(class_name)
            card_div.querySelector('.face')!.classList.add(class_name2)
            
            CardAnimation.setAnimeTime('damage', () => {
                card_div.querySelector('.face')!.classList.remove(class_name)
            })

            CardAnimation.setAnimeTime('damage2', () => {
                card_div.querySelector('.face')!.classList.remove(class_name2)
            })
        }
        function animation_gain_status(card_div: HTMLElement, status_name: string) {
            let class_name = 'gain-status-' + status_name
            card_div.classList.add(class_name)
            Lib.resetAndRemoveAnimation(card_div, "gain-status")

            CardAnimation.setAnimeTime('status', () => {
                card_div.classList.remove(class_name)
            })
        }
        function animation_dealt_encounter_card(card_div: HTMLElement) {
            card_div.classList.remove(dealt_encounter_card)

            requestAnimationFrame(() => {
                card_div.classList.add(dealt_encounter_card)
            })

            CardAnimation.setAnimeTime('dealt', () => {
                card_div.classList.remove(dealt_encounter_card)
            })
        }
        function animation_reveal(card_div: HTMLElement) {
            HoverCard.setReveal(card_div, UI.anime_time * 100 * 8)
            CardAnimation.setAnimeTime('reveal')
        }
        function animation_peek(card_divs: HTMLElement[]) {
            CardAnimation.has_anime += 1;

            HoverCard.hide()

            for( const [i, card_div] of card_divs.entries() ) {
                card_div.classList.add(ClassName.look_at_card)
                const index = card_divs.length - i - 1
                card_div.style.setProperty('--look-at-index', index.toString())
            }

            const timer = CardAnimation.setAnimeTime('peek', () => {
                for( const card_div of card_divs ) {
                    card_div.classList.remove(ClassName.look_at_card)
                }
            })

            CardAnimation.timer_objects[timer] = card_divs
        }
        function animation_resolve_ability(card_div: HTMLElement) {
            HoverCard.setReveal(card_div, UI.anime_time * 1000 * 8)
            CardAnimation.setAnimeTime('ability')
        }
        function animation_attack_thwart(card_div: HTMLElement, card_div2: HTMLElement, class_name: string) {
            let offset = Lib.client.getOffset(card_div)
            let ox = offset.left
            let oy = offset.top

            let offset2 = Lib.client.getOffset(card_div2)
            let nx = offset2.left
            let ny = offset2.top

            // void card_div.offsetWidth;
            card_div.classList.add(class_name)
            let deg = 0
            if( oy > ny) {
                deg = Math.atan2((ny-oy), (nx-ox))*45 + 90
            } else {
                deg = Math.atan2((ny-oy), (nx-ox))*45 - 90
            }

            card_div.classList.add(ClassName.card_moving)

            requestAnimationFrame(() => {
                card_div.style.transform = `translate3d(${nx}px, ${ny}px, 10px) rotate(${deg}deg)`;
            })

            CardAnimation.setAnimeTime('attack', () => {
                card_div.style.transform = ""
            })

            CardAnimation.setAnimeTime('attack2', () => {
                card_div.classList.remove(class_name)
                card_div.classList.remove(ClassName.card_moving)
            })
        }
        function animation_target(card_div2: HTMLElement, card_div: HTMLElement, class_name: string) {
            HoverCard.whenCardActive(card_div2)
            HoverCard.whenCardActive(card_div)
            
            UI.drawLine(card_div2, card_div, class_name)
            CardAnimation.setAnimeTime('target')
        }

        ////////////////////////////////////////////////////////////////////////////////
        //
        if( CardAnimation.animation_name == "shock" ) {
            for( let i = 0; i<active_card_object_ids.length; i++ ) {
                const card_div = Cards.getDiv(active_card_object_ids[i])!
                animation_shock(card_div)
            }
        }
        else if( CardAnimation.animation_name == "damage" ) {
            for( let i = 0; i<active_card_object_ids.length; i++ ) {
                const card_div = Cards.getDiv(active_card_object_ids[i])!
                animation_damage(card_div)
            }
        }
        else if( CardAnimation.animation_name == "gain_status" ) {
            const object_id = active_card_object_ids[1]
            const card_div = Cards.getDiv(object_id)!
            animation_gain_status(card_div, '')
        }
        else if( CardAnimation.animation_name == "being_attacked" ) {
            const target_div = Cards.getDiv(active_card_object_ids[0])!
            target_div.classList.add(ClassName.attack_target)
            CardAnimation.setAnimeTime('target', () => {
                target_div.classList.remove(ClassName.attack_target)
            })
        }
        else if( CardAnimation.animation_name == "peek" ) {
            const card_divs = []
            for( let i = 0; i<active_card_object_ids.length; i++ ) {
                const card_div = Cards.getDiv(active_card_object_ids[i])!
                card_divs.push(card_div)
            }
            animation_peek(card_divs)
        }
        else
        if( CardAnimation.animation_name == "reveal" ) {
            // only show first one
            const card_div = Cards.getDiv(active_card_object_ids[0])!
            animation_reveal(card_div)
        }
        else
        if( CardAnimation.animation_name == "activate" ) {
            // only show first one
            const card_div = Cards.getDiv(active_card_object_ids[0])!
            animation_reveal(card_div)
        }
        else if( CardAnimation.animation_name == "dealt_encounter_card" ) {
            const card_div0 = Cards.getDiv(active_card_object_ids[0])!
            const card_div1 = Cards.getDiv(active_card_object_ids[1])!
            animation_dealt_encounter_card(card_div1)
            animation_target(card_div0, card_div1, CardAnimation.animation_name)
        }
        else
        if( CardAnimation.animation_name == "scheme" || CardAnimation.animation_name == "thwart" || CardAnimation.animation_name == "attack"  ) {
            const card_div0 = Cards.getDiv(active_card_object_ids[0])!
            const card_div1 = Cards.getDiv(active_card_object_ids[1])!
            if( card_div0 != card_div1 ) {
                animation_attack_thwart(card_div1, card_div0, CardAnimation.animation_name)
            }
        }
        else
        if( CardAnimation.animation_name == "target_engaged" ) {
            const card_div0 = Cards.getDiv(active_card_object_ids[0])!  // minion
            const card_div1 = Cards.getDiv(active_card_object_ids[1])!  // player
            const card_div2 = Cards.getDiv(active_card_object_ids[2])!  // effect
            animation_target(card_div0, card_div1, "target")
            animation_target(card_div2, card_div0, "target")
        }
        else
        if( CardAnimation.animation_name.startsWith("target") ) {
            // target   A <- B C D
            // target2  A -> B C D
            // target3  A B C <- D
            let is_target2 = CardAnimation.animation_name.startsWith("target2")
            let is_target3 = CardAnimation.animation_name.startsWith("target3")
            CardAnimation.animation_name = CardAnimation.animation_name.replace("target2", "target")
            CardAnimation.animation_name = CardAnimation.animation_name.replace("target3", "target")

            if( CardAnimation.animation_name == "target_ability" ) {
                const card_div = Cards.getDiv(active_card_object_ids[0])!
                animation_resolve_ability(card_div)
            }

            if( is_target3 ) {
                const target3_object_id = active_card_object_ids[active_card_object_ids.length-1]
                const card_div0 = Cards.getDiv(target3_object_id)!
                if( Cards.getCard(target3_object_id)!.card_type != "Insert" ) {
                    for( let i = 0; i<active_card_object_ids.length-1; i++ ) {
                        const card_div_i = Cards.getDiv(active_card_object_ids[i])!
                        if( card_div0 != card_div_i ) {
                            animation_target(card_div0, card_div_i, CardAnimation.animation_name)
                        }
                    }
                }
            }
            else {
                const card_div0 = Cards.getDiv(active_card_object_ids[0])!
                // if( CardAnimation.animation_name == "target_apply" ) {
                //     animation_resolve_ability(card_div0)
                // }
                for( let i = 1; i<active_card_object_ids.length; i++ ) {
                    const card_div_i = Cards.getDiv(active_card_object_ids[i])!
                    if( card_div0 != card_div_i ) {
                        if( CardAnimation.animation_name == "target_reveal" ) {
                            if( !card_div0.parentElement?.classList.contains('dealt-encounter-cards') ) {
                                continue
                            }
                        }
                        if( is_target2 ) {
                            animation_target(card_div0, card_div_i, CardAnimation.animation_name)
                        } else {
                            animation_target(card_div_i, card_div0, CardAnimation.animation_name)
                        }
                    }
                }
            }
        }
        else
        if( CardAnimation.animation_name == "center_flip" ) {
            const object_id = active_card_object_ids[0]
            const card_div = Cards.getDiv(object_id)!
            if( card_div.parentElement!.id == 'area-removed' ||
                card_div.parentElement!.id == 'area-play' ||
                card_div.parentElement!.id.includes('-special-deck-') ||
                card_div.parentElement!.id.endsWith('player-deck') ||
                card_div.parentElement!.id.endsWith('discard-pile') ||
                card_div.parentElement!.id.endsWith('additional-deck') ||
                card_div.parentElement!.id.endsWith('dealt-encounter-cards')) {
                if( ButtonSetting.pause_when_reveal_or_boost && !UI.hold_ctrl && !ButtonSetting.is_replay ) {
                    HoverCard.center_preview.set(card_div, true)
                    Button.enablePause()
                } else {
                    // CardAnimation.has_anime += 1
                    // const timeout = 4000
                    // setTimeout(() => {
                    //     CardAnimation.has_anime -= 1
                    //     HoverCard.hide()
                    // }, UI.anime_time * timeout);
                }
            }
        }
    }

    static activeCard(card_div: HTMLElement, old_parent: HTMLElement|null) {
        const object_id = Number(card_div.dataset.id!)
        if( !CardAnimation.active_card_object_ids.includes(object_id) ) {
            return
        }

        let name: 'activate'|'activate_area'|'activate_facedown' = 'activate'
        if( Cards.getCard(object_id)!.is_face_up &&
            card_div.parentElement &&
            card_div.parentElement == old_parent
        ) {
            name = 'activate_area'
        }
        else
        if( !Cards.getCard(object_id)!.is_face_up ) {
            name = 'activate_facedown'
        }

        card_div.classList.add(ClassName.active_card)
        
        HoverCard.whenCardActive(card_div)
        
        CardAnimation.setAnimeTime(name)
    }

    static flipCard(card_div: HTMLElement) {
        card_div.classList.add(ClassName.card_flipping)

        if( !card_div.classList.contains(ClassName.card_moving) ) {
            MoveCard.resetAreaXY(card_div.parentElement!, Array.from(card_div.parentElement!.getElementsByClassName('card') as HTMLCollectionOf<HTMLElement>))
        }

        CardAnimation.setAnimeTime('flip', () => {
            card_div.classList.remove(ClassName.card_flipping)
        });
    }

    static moveCard(card_div: HTMLElement, parent_element: HTMLElement, old_parent: HTMLElement|null, index: number, shuffle: boolean) {
        const timeout = 1500
        if( old_parent ) {
            Lib.resetAndRemoveAnimation(old_parent, ClassName.deck_change_size)
        }
        MoveCard.appendChildWithCallback(parent_element, card_div, index, timeout)
        Lib.resetAndRemoveAnimation(parent_element, ClassName.deck_change_size)

        CardAnimation.has_anime += 1
        CardAnimation.setAnimeTime2(UI.anime_time * timeout)

        setTimeout(function() {
            CardAnimation.has_anime -= 1
        }, UI.anime_move_time * timeout);
    }

    static shuffleCard(card_div: HTMLElement, parent_element: HTMLElement, index: number) {
        parent_element.insertBefore(card_div, parent_element.childNodes[index]);
        card_div.style.setProperty('--rand', Math.random().toString())
        card_div.classList.add(ClassName.card_shuffle)

        CardAnimation.setAnimeTime('shuffle', () => {
            card_div.classList.remove(ClassName.card_shuffle)
        })
    }
}
