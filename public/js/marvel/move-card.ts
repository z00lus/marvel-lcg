import { UI } from "./ui.js";
import { ClassName } from './class_name.js'
import { Cards } from "./cards.js";
import { Setting } from "./settings.js";
import { Lib } from "./lib.js";

export class MoveCard {

    // Root CSS custom properties
    static rootStyles = getComputedStyle(document.documentElement);
    static cardWidth = parseFloat(MoveCard.rootStyles.getPropertyValue('--card-width'));
    static cardHeight = parseFloat(MoveCard.rootStyles.getPropertyValue('--card-height'));

    static timer: Record<string, number> = {}
    static updating_area: Set<HTMLElement> = new Set()
    static updating_in_deck_cards: Set<HTMLElement> = new Set()

    static refreshDimensions() {
        MoveCard.rootStyles = getComputedStyle(document.documentElement);
        MoveCard.cardWidth = parseFloat(MoveCard.rootStyles.getPropertyValue('--card-width'));
        MoveCard.cardHeight = parseFloat(MoveCard.rootStyles.getPropertyValue('--card-height'));
    }

    static narrowToRange(values: number[], newMin: number, newMax: number): number[] {
        const oldMin = Math.min(...values);
        const oldMax = Math.max(...values);
        
        const oldRange = oldMax - oldMin;
        const newRange = newMax - newMin;
    
        return values.map(value => {
            // Shift and scale
            return ((value - oldMin) * newRange) / oldRange + newMin;
        });
    }

    static resetAreaXY(parent: HTMLElement, cards_els: HTMLElement[]) {
        if (parent.classList.contains('deck')) return;

        MoveCard.refreshDimensions();

        const shown_cards_els = cards_els.filter(x => !x.classList.contains('hide'));
        if (shown_cards_els.length === 0) return;

        const sceneWidth = parseFloat(MoveCard.rootStyles.getPropertyValue('--scene-width'));
        let { padding, padding2 } = MoveCard.getPadding(parent);

        // Build the list of x increments for each card, with area-specific rules
        let list_x: number[] = [];
        let card_area: string | null = null;

        if (parent.id === "player-all-hand-cards") {
            MoveCard.buildHandXList(shown_cards_els, list_x);
        } else if (parent.id === 'area-play') {
            MoveCard.buildPlayAreaXList(shown_cards_els, list_x);
        } else if (parent.classList.contains('dealt-encounter-cards')) {
            MoveCard.buildDealtEncounterXList(shown_cards_els, list_x);
        } else {
            card_area = "area";
            MoveCard.buildAreaXList(parent, shown_cards_els, list_x, padding);
        }

        // Calculate the total width of all cards in the area
        let all_cards_width = MoveCard.calculateTotalWidth(list_x, padding, padding2);

        // Calculate the offset for the area based on parent type/context
        const offsets = MoveCard.computeOffsets(parent, all_cards_width, sceneWidth, padding);
        // Distribute cards along the x-axis with computed offset
        let list_x2 = MoveCard.computeCardPositions(list_x, offsets.offset_x, padding, padding2);

        if( list_x2[0] < 0 ) {
            // Fix "32158"
            list_x2 = MoveCard.narrowToRange(list_x2, padding, list_x2[list_x2.length - 1]);
        }
        else
        // Handle overflow (cards exceeding area width)
        if (offsets.over_screen) {
            list_x2 = MoveCard.distributeOverflow(list_x2, sceneWidth, offsets.sceneWidth2);
        }

        // Set final x/y positions on each card element
        MoveCard.setCardStyles(shown_cards_els, cards_els, list_x2, parent, card_area, offsets.normal_y, offsets.scheme_upgrade_y);
        MoveCard.positionBoundStatusCards(shown_cards_els);
    }

    private static getPadding(parent: HTMLElement) {
        let padding = MoveCard.cardWidth * 0.5;
        let padding2 = MoveCard.cardWidth;
        if (
            parent.id === 'area-schemes-side' ||
            parent.id === 'area-schemes-main' ||
            parent.classList.contains('area-hero') ||
            parent.classList.contains('supports')
        ) {
            padding = MoveCard.cardWidth * 0.3;
        } else if (parent.id === "player-all-hand-cards") {
            padding = MoveCard.cardWidth * 1;
        }
        return { padding, padding2 };
    }

    private static buildHandXList(cards_els: HTMLElement[], list_x: number[]) {
        const show_all_hands = true;
        for (let i = 0; i < cards_els.length; i++) {
            let x = MoveCard.cardWidth;
            if (show_all_hands && i > 0) {
                let id_a = Number(cards_els[i].dataset.id!);
                let id_b = Number(cards_els[i - 1].dataset.id!);
                if (Cards.getCard(id_a)!.control_player !== Cards.getCard(id_b)!.control_player) {
                    list_x.push(-2);
                }
            }
            list_x.push(x);
        }
    }

    private static buildPlayAreaXList(cards_els: HTMLElement[], list_x: number[]) {
        for (let i = 0; i < cards_els.length; i++) {
            list_x.push(MoveCard.cardWidth + 10);
        }
    }

    private static buildDealtEncounterXList(cards_els: HTMLElement[], list_x: number[]) {
        for (let i = cards_els.length - 1; i >= 0; i--) {
            list_x.push(MoveCard.cardWidth * 0.5);
        }
    }

    private static buildAreaXList(parent: HTMLElement, cards_els: HTMLElement[], list_x: number[], padding: number) {
        let rendered_ids: number[] = [];
        let end_offset_x = 0;
        const statusCountByTarget = new Map<number, number>();
        for (let i = cards_els.length - 1; i >= 0; i--) {
            const object_id = Number(cards_els[i].dataset.id!);
            const card = Cards.getCard(object_id)!;
            let x = MoveCard.computeCardX(card, list_x, statusCountByTarget);

            // Insert padding for grouped/bound cards
            if (!rendered_ids.includes(card.bind_object_id) && i !== cards_els.length - 1 && !card.is_dealt_card) {
                list_x[list_x.length - 1] += end_offset_x;
                list_x.push(-1); // Use -1 as a marker for padding
                rendered_ids = [];
            }

            if (card.is_face_up) end_offset_x = 0;
            list_x.push(x);
            rendered_ids.push(object_id);

            // Debug mode: set a debug property for visualizing card widths
            if (Setting.is_debug) {
                let all_cards_width = MoveCard.calculateTotalWidth(list_x, padding, MoveCard.cardWidth);
                cards_els[i].style.setProperty('--x', all_cards_width.toString());
            }
        }
        list_x[list_x.length - 1] += end_offset_x;
    }

    private static computeCardX(card: any, list_x: number[], statusCountByTarget: Map<number, number>): number {
        let x = 0;
        if (!card.is_face_up) {
            // Shift left for face-down cards
            const old_x = list_x.pop()!;
            if (old_x) list_x.push(old_x - MoveCard.cardWidth * 0.5);
            x += MoveCard.cardWidth;
        } else {
            switch (card.card_type) {
                case "Challenge":
                    x += MoveCard.cardHeight;
                    break;
                case "Hero":
                case "AlterEgo":
                case "EncounterVillain":
                    if (card.name === "Archangel") {
                        x += MoveCard.cardWidth * 2;
                    } else if ('t_GIANT' in card.traits) {
                        x += MoveCard.cardHeight;
                    } else {
                        x += MoveCard.cardWidth;
                    }
                    break;
                case "StatusCard":
                    if (card.bind_object_id) {
                        const statusCount = statusCountByTarget.get(card.bind_object_id) ?? 0;
                        statusCountByTarget.set(card.bind_object_id, statusCount + 1);
                        x += MoveCard.cardWidth * (statusCount === 0 ? 0.65 : 0.15);
                    } else {
                        x += MoveCard.cardWidth * 0.5;
                    }
                    break;
                default:
                    if (card.card_type_base === "Scheme") {
                        x += MoveCard.cardHeight;
                    } else {
                        x += MoveCard.cardWidth;
                    }
                    break;
            }
        }
        return x;
    }

    private static calculateTotalWidth(list_x: number[], padding: number, padding2: number) {
        return list_x.reduce((sum, val) => {
            if (val === -1) return sum + padding;
            if (val === -2) return sum + padding2;
            return sum + val;
        }, 0);
    }

    private static computeOffsets(parent: HTMLElement, all_cards_width: number, sceneWidth: number, padding: number) {
        const parentStyles = getComputedStyle(parent);
        const normal_y = Number(parentStyles.getPropertyValue('--y'));
        const scheme_upgrade_y = normal_y - (MoveCard.cardHeight - MoveCard.cardWidth) * 0.5;

        const layoutLeft = parseFloat(parentStyles.getPropertyValue('--layout-left'));
        const layoutWidth = parseFloat(parentStyles.getPropertyValue('--layout-width'));
        const hasLayoutLane = Number.isFinite(layoutLeft) && Number.isFinite(layoutWidth) && layoutWidth > 0;

        let sceneWidth2 = hasLayoutLane ? layoutWidth : sceneWidth - MoveCard.cardWidth * 1.5;
        if (!hasLayoutLane && parent.id === 'area-villain') {
            sceneWidth2 *= 0.6;
        }

        let offset_x = 0;
        let over_screen = false;
        if (parent.classList.contains('area-center')) {
            if (all_cards_width > sceneWidth2) {
                all_cards_width = sceneWidth2;
                over_screen = true;
            }
            offset_x = hasLayoutLane
                ? Math.round(layoutLeft + (layoutWidth - all_cards_width) * 0.5)
                : Math.round((sceneWidth - all_cards_width) * 0.5);
            if (offset_x.toString() !== parent.style.getPropertyValue('--x')) {
                parent.style.setProperty('--x', offset_x.toString());
            }
        } else if (parent.classList.contains('area-schemes')) {
            offset_x = Number(parentStyles.getPropertyValue('--x')) - all_cards_width;
        } else {
            offset_x = Number(parentStyles.getPropertyValue('--x'));
        }

        return { offset_x, over_screen, normal_y, scheme_upgrade_y, sceneWidth2 };
    }

    private static computeCardPositions(list_x: number[], offset_x: number, padding: number, padding2: number) {
        let cumulative_sum = offset_x;
        let list_x2: number[] = [];
        for (let i = 0; i < list_x.length; i++) {
            if (list_x[i] === -1) {
                cumulative_sum += padding;
            } else if (list_x[i] === -2) {
                cumulative_sum += padding2;
            } else {
                list_x2.push(cumulative_sum);
                cumulative_sum += list_x[i];
            }
        }
        return list_x2;
    }

    private static distributeOverflow(list_x2: number[], sceneWidth: number, sceneWidth2: number) {
        const diff = (list_x2[list_x2.length - 1] - list_x2[0] + MoveCard.cardWidth) - sceneWidth2;
        const size = diff / (list_x2.length - 1);
        return list_x2.map((num, index) => Math.round(num - size * index));
    }

    private static setCardStyles(
        cards_els: HTMLElement[],
        all_cards_els: HTMLElement[],
        list_x2: number[],
        parent: HTMLElement,
        card_area: string | null,
        normal_y: number,
        scheme_upgrade_y: number
    ) {
        for (let j = 0, j2=0; j < all_cards_els.length; j++) {
            const i = card_area === "area" ? all_cards_els.length - j - 1 : j;
            const c = all_cards_els[i];
            let x = j2 < list_x2.length ? list_x2[j2] : list_x2[list_x2.length-1];

            // Special y-position for scheme upgrades
            let y = normal_y;
            if (
                c.parentElement!.id === 'area-schemes-main' ||
                c.parentElement!.id === 'area-schemes-side'
            ) {
                if (
                    c.classList.contains('facedown') || (
                        !c.classList.contains('type-main-scheme') &&
                        !c.classList.contains('type-encounter-side-scheme') &&
                        !c.classList.contains('type-player-side-scheme')
                    )
                ) {
                    y = scheme_upgrade_y;
                }
            }

            // Only update if changed
            let x_s = x.toString();
            let y_s = y.toString();
            let g_x = c.style.getPropertyValue('--x');
            let g_y = c.style.getPropertyValue('--y');
            if (x_s !== g_x && y_s !== g_y) {
                c.style.setProperty('--x', x_s);
                c.style.setProperty('--y', y_s);
            } else if (x_s !== g_x) {
                c.style.setProperty('--x', x_s);
            } else if (y_s !== g_y) {
                c.style.setProperty('--y', y_s);
            }

            if( cards_els.includes(c) ) {
                j2 += 1;
            }
        }
    }

    private static positionBoundStatusCards(cards_els: HTMLElement[]) {
        const statusIndexByTarget = new Map<number, number>();
        const sortedStatusCards = cards_els
            .map(element => ({
                element,
                card: Cards.getCard(Number(element.dataset.id!)),
            }))
            .filter(item =>
                item.card?.card_type === 'StatusCard' &&
                item.card.bind_object_id !== 0
            )
            .sort((a, b) => a.card!.object_id - b.card!.object_id);

        for (const { element, card } of sortedStatusCards) {
            const target = Cards.getDiv(card!.bind_object_id);
            if (!target || target.parentElement !== element.parentElement || target.classList.contains('hide')) {
                continue;
            }

            const stackIndex = statusIndexByTarget.get(card!.bind_object_id) ?? 0;
            statusIndexByTarget.set(card!.bind_object_id, stackIndex + 1);

            const targetX = Number(target.style.getPropertyValue('--x'));
            const targetY = Number(target.style.getPropertyValue('--y'));
            // A clockwise rotation moves the artwork's title edge to the
            // right. Leave that strip visible while the rest stays under
            // the bound character card.
            const x = targetX + MoveCard.cardWidth * (0.65 + stackIndex * 0.15);
            const y = targetY + stackIndex * 10;

            element.style.setProperty('--x', x.toString());
            element.style.setProperty('--y', y.toString());
        }
    }

    static appendChildWithCallback(
        parent: HTMLElement,
        child: HTMLElement,
        index = -1,
        timeout = 1500,
        first_create = false
    ) {
        // Don't re-insert if already at correct position
        if (parent.children[index] === child) return;
        if (index < 0) index = parent.children.length;

        // Queue area update for old parent
        if (child.parentElement && child.parentElement.classList.contains('area')) {
            if (!child.parentElement.classList.contains('hide-player')) {
                MoveCard.updating_area.add(child.parentElement);
            }
        }

        // Animate card shuffle/move if not first create
        if (child.parentElement !== parent && !UI.global_first_create) {
            child.style.setProperty('--rand', Math.random().toString());
            child.classList.add(ClassName.card_moving, ClassName.card_shuffle);
        }

        parent.insertBefore(child, parent.children[index] || null);

        // Queue area update for new parent
        if (!parent.classList.contains('hide-player')) {
            MoveCard.updating_area.add(parent);
        }

        // Handle animation classes and timer
        if (!UI.global_first_create) {
            if (!parent.classList.contains('area')) {
                MoveCard.updating_in_deck_cards.add(child);
            }

            timeout = UI.anime_move_time * timeout
            const child_id = child.dataset.id as string;
            if (MoveCard.timer[child_id]) {
                clearTimeout(MoveCard.timer[child_id]);
            }
            MoveCard.timer[child_id] = setTimeout(() => {
                child.classList.remove(ClassName.card_moving);
                delete MoveCard.timer[child_id];
                child.classList.remove(ClassName.card_shuffle);
                setTimeout(() => {
                    child.classList.remove(ClassName.card_shuffle);
                }, 3 * timeout);
            }, 1 * timeout);
        }
    }

    static doMoveFirstTime() {
        MoveCard.refreshDimensions();

        document.querySelectorAll<HTMLElement>('.deck:not(.area)').forEach(parent => {
            const parentStyles = getComputedStyle(parent)
            const y = Number(parentStyles.getPropertyValue('--y'))
            const x = Number(parentStyles.getPropertyValue('--x'))
            parent.querySelectorAll<HTMLElement>('.card').forEach(c => {
                c.style.setProperty('--x', x.toString());
                c.style.setProperty('--y', y.toString());
            })
        });

        const areas = document.querySelectorAll<HTMLElement>('.area');
        areas.forEach(parent => {
            const cards_els = Array.from(parent.getElementsByClassName('card') as HTMLCollectionOf<HTMLElement>);
            MoveCard.resetAreaXY(parent, cards_els);
        });

        MoveCard.updating_area.clear();
    }

    static doMove() {
        const areas: HTMLElement[] = Array.from(MoveCard.updating_area);
        const card_divs: HTMLElement[] = Array.from(MoveCard.updating_in_deck_cards);
        MoveCard.updating_area.clear();
        MoveCard.updating_in_deck_cards.clear();

        // Animate in-deck cards
        if (card_divs.length > 0) {
            const styleCache: Map<HTMLElement, { x: number; y: number }> = new Map();
            card_divs.forEach(c => {
                const parent = c.parentElement;
                if (parent) {
                    if (!styleCache.has(parent)) {
                        if (parent instanceof HTMLElement) {
                            const parentStyles = getComputedStyle(parent);
                            styleCache.set(parent, {
                                x: Number(parentStyles.getPropertyValue('--x')),
                                y: Number(parentStyles.getPropertyValue('--y')),
                            });
                        } else {
                            Lib.alert(`${parent} ${c}`);
                        }
                    }
                    const { x, y } = styleCache.get(parent)!;
                    c.classList.add(ClassName.card_moving, ClassName.card_shuffle);
                    c.style.setProperty('--x', x.toString());
                    c.style.setProperty('--y', y.toString());
                }
            });
        }

        // Animate and update card area layouts, using rAF for smoothness
        (function processAreas(index: number) {
            if (index < areas.length) {
                const parent = areas[index];
                const cards_els = Array.from(parent.getElementsByClassName('card') as HTMLCollectionOf<HTMLElement>);
                MoveCard.resetAreaXY(parent, cards_els);
                requestAnimationFrame(() => processAreas(index + 1));
            }
        })(0);
    }

    static doMoveFocusOnPlayer(areas: HTMLElement[]) {
        MoveCard.updating_area.clear();
        areas.forEach(parent => {
            const cards_els = Array.from(parent.getElementsByClassName('card') as HTMLCollectionOf<HTMLElement>);
            MoveCard.resetAreaXY(parent, cards_els);
        });
    }
}
