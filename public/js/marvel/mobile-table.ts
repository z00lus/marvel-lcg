import { MoveCard } from './move-card.js';
import { adjustSceneScale } from './scene.js';
import { Setting } from './settings.js';

type MobileTableMode = 'board' | 'focus';

interface AuxiliaryZone {
    id: string;
    label: string;
    targetOnly?: boolean;
}

export class MobileTable {
    private static readonly media = Setting.mobile_table_media;
    private static readonly storageKey = 'ronin-mobile-table-mode';
    private static readonly zones: AuxiliaryZone[] = [
        { id: `player-${Setting.player_id}-additional-deck`, label: 'Additional deck' },
        { id: `player-${Setting.player_id}-additional-discard-pile`, label: 'Additional discard' },
        { id: `player-${Setting.player_id}-special-deck-0`, label: 'Special deck I' },
        { id: `player-${Setting.player_id}-special-deck-1`, label: 'Special deck II' },
        { id: 'victory-display', label: 'Victory display' },
        { id: 'area-removed', label: 'Set aside' },
        { id: 'nemesis-pool', label: 'Nemesis set' },
        { id: 'area-advanced', label: 'Villain stages' },
        { id: 'removed-pool', label: 'Status pool', targetOnly: true },
    ];

    private static mode: MobileTableMode = 'board';
    private static active = false;
    private static activeZoneId = '';
    private static layoutFrame = 0;
    private static updateFrame = 0;
    private static observer: MutationObserver | null = null;
    private static targetState = new Map<string, boolean>();

    static init() {
        MobileTable.mode = MobileTable.loadMode();
        MobileTable.createZoneButtons();
        MobileTable.bindControls();
        MobileTable.observeZones();
        MobileTable.updateViewport();

        MobileTable.media.addEventListener('change', () => MobileTable.updateViewport());
        window.addEventListener('orientationchange', () => MobileTable.requestLayout());
        window.addEventListener('resize', () => {
            if (MobileTable.active) MobileTable.requestLayout();
        });
    }

    private static loadMode(): MobileTableMode {
        try {
            return localStorage.getItem(MobileTable.storageKey) === 'focus' ? 'focus' : 'board';
        } catch {
            return 'board';
        }
    }

    private static saveMode() {
        try {
            localStorage.setItem(MobileTable.storageKey, MobileTable.mode);
        } catch {
            // Private browsing can make localStorage unavailable. The layout
            // still works for the current page in that case.
        }
    }

    private static bindControls() {
        document.querySelectorAll<HTMLButtonElement>('#mobile-table-toolbar [data-mobile-mode]').forEach(button => {
            button.addEventListener('click', () => {
                const mode = button.dataset.mobileMode;
                if (mode === 'board' || mode === 'focus') MobileTable.setMode(mode);
            });
        });

        document.getElementById('mobile-zones-toggle')?.addEventListener('click', () => {
            if (document.documentElement.classList.contains('mobile-table-zones-open')) {
                MobileTable.closeZones();
            } else {
                MobileTable.openZones(MobileTable.firstAvailableZone());
            }
        });

        document.getElementById('mobile-zone-close')?.addEventListener('click', () => MobileTable.closeZones());
        document.getElementById('mobile-zone-drawer-plane')?.addEventListener('click', event => {
            if (event.target === event.currentTarget) MobileTable.closeZones();
        });
    }

    private static createZoneButtons() {
        const container = document.getElementById('mobile-zone-list');
        if (!container) return;

        for (const zone of MobileTable.zones) {
            const button = document.createElement('button');
            button.type = 'button';
            button.dataset.zoneId = zone.id;
            button.innerHTML = `<span>${zone.label}</span><output>0</output>`;
            button.addEventListener('click', () => MobileTable.openZones(zone.id));
            container.appendChild(button);
        }
    }

    private static observeZones() {
        const scene = document.getElementById('scene');
        if (!scene) return;

        for (const zone of MobileTable.zones) {
            document.getElementById(zone.id)?.classList.add('mobile-auxiliary-zone');
        }

        MobileTable.observer = new MutationObserver(() => MobileTable.requestZoneUpdate());
        MobileTable.observer.observe(scene, {
            childList: true,
            subtree: true,
            attributes: true,
            attributeFilter: ['class', 'data-total_cards'],
        });
        MobileTable.updateZones();
    }

    private static requestZoneUpdate() {
        if (MobileTable.updateFrame) return;
        MobileTable.updateFrame = requestAnimationFrame(() => {
            MobileTable.updateFrame = 0;
            MobileTable.updateZones();
        });
    }

    private static updateZones() {
        let availableCount = 0;

        for (const zone of MobileTable.zones) {
            const zoneElement = document.getElementById(zone.id);
            const button = document.querySelector<HTMLButtonElement>(`#mobile-zone-list [data-zone-id="${zone.id}"]`);
            if (!zoneElement || !button) continue;

            const count = Number(zoneElement.dataset.total_cards || zoneElement.children.length || 0);
            const hasTarget = Boolean(zoneElement.querySelector('.highlight-targets, .highlight-effect, .selected'));
            const wasTarget = MobileTable.targetState.get(zone.id) ?? false;
            const available = hasTarget || (!zone.targetOnly && count > 0);

            MobileTable.targetState.set(zone.id, hasTarget);
            button.hidden = !available;
            button.classList.toggle('has-target', hasTarget);
            button.querySelector('output')!.textContent = String(count);
            if (available) availableCount += 1;

            if (MobileTable.active && hasTarget && !wasTarget) {
                MobileTable.openZones(zone.id);
            }
        }

        const toggle = document.getElementById('mobile-zones-toggle');
        if (toggle) {
            toggle.dataset.count = String(availableCount);
            toggle.classList.toggle('has-zones', availableCount > 0);
        }

        if (MobileTable.activeZoneId) {
            const activeButton = document.querySelector<HTMLButtonElement>(
                `#mobile-zone-list [data-zone-id="${MobileTable.activeZoneId}"]`
            );
            if (!activeButton || activeButton.hidden) {
                const nextZone = MobileTable.firstAvailableZone();
                if (nextZone) MobileTable.openZones(nextZone);
                else MobileTable.closeZones();
            }
        }
    }

    private static firstAvailableZone(): string {
        return document.querySelector<HTMLButtonElement>('#mobile-zone-list button:not([hidden])')?.dataset.zoneId ?? '';
    }

    private static updateViewport() {
        MobileTable.active = MobileTable.media.matches;
        const root = document.documentElement;
        const body = document.body;

        root.classList.toggle('mobile-table-active', MobileTable.active);
        body.classList.toggle('mobile-table-active', MobileTable.active);

        if (MobileTable.active) {
            MobileTable.applyModeClasses();
        } else {
            root.classList.remove('mobile-table-board', 'mobile-table-focus', 'mobile-table-zones-open');
            body.classList.remove('mobile-table-board', 'mobile-table-focus', 'mobile-table-zones-open');
            MobileTable.closeZones(false);
        }

        MobileTable.requestLayout();
    }

    private static setMode(mode: MobileTableMode) {
        if (MobileTable.mode === mode) return;
        MobileTable.mode = mode;
        MobileTable.saveMode();
        MobileTable.closeZones(false);
        MobileTable.applyModeClasses();
        MobileTable.requestLayout();
    }

    private static applyModeClasses() {
        const root = document.documentElement;
        const body = document.body;
        for (const element of [root, body]) {
            element.classList.toggle('mobile-table-board', MobileTable.mode === 'board');
            element.classList.toggle('mobile-table-focus', MobileTable.mode === 'focus');
        }

        document.querySelectorAll<HTMLButtonElement>('#mobile-table-toolbar [data-mobile-mode]').forEach(button => {
            button.classList.toggle('active', button.dataset.mobileMode === MobileTable.mode);
            button.setAttribute('aria-pressed', String(button.dataset.mobileMode === MobileTable.mode));
        });
    }

    private static openZones(zoneId: string) {
        if (!MobileTable.active || !zoneId) return;
        const zoneElement = document.getElementById(zoneId);
        if (!zoneElement) return;

        MobileTable.clearActiveZone();
        MobileTable.activeZoneId = zoneId;
        zoneElement.classList.add('mobile-zone-active');
        MobileTable.positionActiveZone();

        document.documentElement.classList.add('mobile-table-zones-open');
        document.body.classList.add('mobile-table-zones-open');
        document.getElementById('mobile-zone-picker')?.removeAttribute('hidden');
        document.getElementById('mobile-zones-toggle')?.setAttribute('aria-expanded', 'true');

        document.querySelectorAll<HTMLButtonElement>('#mobile-zone-list [data-zone-id]').forEach(button => {
            button.classList.toggle('active', button.dataset.zoneId === zoneId);
        });
        MobileTable.requestLayout();
    }

    private static positionActiveZone() {
        const zoneElement = document.getElementById(MobileTable.activeZoneId);
        if (!zoneElement) return;

        const rootStyles = getComputedStyle(document.documentElement);
        const sceneWidth = parseFloat(rootStyles.getPropertyValue('--scene-width'));
        const sceneHeight = parseFloat(rootStyles.getPropertyValue('--scene-height'));
        const cardWidth = parseFloat(rootStyles.getPropertyValue('--card-width'));
        const cardHeight = parseFloat(rootStyles.getPropertyValue('--card-height'));
        const zoneX = sceneWidth > sceneHeight
            ? (sceneWidth - cardWidth) * 0.16
            : (sceneWidth - cardWidth) * 0.5;
        zoneElement.style.setProperty('--x', Math.round(zoneX).toString());
        zoneElement.style.setProperty('--y', Math.round((sceneHeight - cardHeight) * 0.48).toString());
    }

    private static closeZones(requestLayout = true) {
        document.documentElement.classList.remove('mobile-table-zones-open');
        document.body.classList.remove('mobile-table-zones-open');
        document.getElementById('mobile-zone-picker')?.setAttribute('hidden', '');
        document.getElementById('mobile-zones-toggle')?.setAttribute('aria-expanded', 'false');
        MobileTable.clearActiveZone();
        MobileTable.activeZoneId = '';
        if (requestLayout) MobileTable.requestLayout();
    }

    private static clearActiveZone() {
        document.querySelectorAll<HTMLElement>('.mobile-auxiliary-zone.mobile-zone-active').forEach(zone => {
            zone.classList.remove('mobile-zone-active', 'clicked');
            zone.style.removeProperty('--x');
            zone.style.removeProperty('--y');
        });
        document.querySelectorAll<HTMLButtonElement>('#mobile-zone-list [data-zone-id]').forEach(button => {
            button.classList.remove('active');
        });
    }

    private static requestLayout() {
        if (MobileTable.layoutFrame) cancelAnimationFrame(MobileTable.layoutFrame);
        MobileTable.layoutFrame = requestAnimationFrame(() => {
            MobileTable.layoutFrame = requestAnimationFrame(() => {
                MobileTable.layoutFrame = 0;
                MobileTable.positionActiveZone();
                MoveCard.doMoveFirstTime();
                adjustSceneScale();
            });
        });
    }
}
