export type MarvelCdbDeckData = {
    name: string;
    deck_name?: string;
    hero: string[];
    player_deck: string[];
    metadata?: Record<string, string>;
};

export type RecentDeck = {
    reference: string;
    name: string;
    hero: string;
};

const recentDecksStorageKey = 'marvel_lcg_recent_marvelcdb_decks';
const recentDeckLimit = 10;

async function postJson<T>(url: string, body: unknown): Promise<T> {
    const response = await fetch(url, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(body),
    });

    let payload: any = null;
    try {
        payload = await response.json();
    } catch (error) {
        throw new Error('The server returned an unreadable response.');
    }

    if (!response.ok) {
        throw new Error(payload?.error ?? `Request failed (${response.status}).`);
    }
    return payload as T;
}

/**
 * Resolve a pasted MarvelCDB link or ID into a playable deck.
 *
 * Nothing is stored server-side: the deck comes back as data and is handed to
 * /new directly, so trying a netdeck leaves nothing behind.
 */
export function resolveMarvelCdbDeck(reference: string): Promise<MarvelCdbDeckData> {
    return postJson<MarvelCdbDeckData>('/resolve_marvelcdb_deck', {deck: reference});
}

export function saveCampaignDeck(
    campaignId: string,
    deck: MarvelCdbDeckData,
): Promise<{hero_id: string; deck: MarvelCdbDeckData}> {
    return postJson('/save_campaign_deck', {campaign_id: campaignId, deck});
}

export function refreshCampaignDeck(
    heroId: string,
): Promise<{hero_id: string; deck: MarvelCdbDeckData; changed: number}> {
    return postJson('/refresh_campaign_deck', {hero_id: heroId});
}

export function loadRecentDecks(): RecentDeck[] {
    try {
        const raw = localStorage.getItem(recentDecksStorageKey);
        if (!raw) {
            return [];
        }
        const parsed = JSON.parse(raw);
        if (!Array.isArray(parsed)) {
            return [];
        }
        return parsed.filter((entry): entry is RecentDeck =>
            typeof entry?.reference === 'string' && typeof entry?.name === 'string');
    } catch (error) {
        console.warn('Ignoring invalid MarvelCDB deck history', error);
        localStorage.removeItem(recentDecksStorageKey);
        return [];
    }
}

/**
 * Remember a deck by reference rather than by contents.
 *
 * Re-picking a recent deck re-resolves it, so an edited netdeck is picked up
 * instead of serving back a stale snapshot from the time it was first played.
 */
export function rememberRecentDeck(entry: RecentDeck): RecentDeck[] {
    const existing = loadRecentDecks().filter(
        (recent) => recent.reference !== entry.reference);
    const updated = [entry, ...existing].slice(0, recentDeckLimit);
    try {
        localStorage.setItem(recentDecksStorageKey, JSON.stringify(updated));
    } catch (error) {
        console.warn('Could not store MarvelCDB deck history', error);
    }
    return updated;
}

/** The card id a deck's hero is identified by, e.g. "60001a". */
export function getDeckHeroCode(deck: {hero?: string[]}): string {
    const [first] = deck.hero ?? [];
    return (first ?? '').split(',')[0]?.trim().toLowerCase() ?? '';
}

export type DeckSourceController = {
    getSource(): 'precon' | 'marvelcdb';
    getDeck(): MarvelCdbDeckData | null;
    isBusy(): boolean;
    clear(): void;
    setDeck(deck: MarvelCdbDeckData, notice: string): void;
};

/**
 * Wire the shared "Precon / MarvelCDB deck" picker.
 *
 * Quick Play and Campaign use identical markup and differ only in what they do
 * once a deck resolves, which is what `onResolved` is for: it returns the text
 * to show, so a page can report a hero switch instead of the deck name.
 */
export function createDeckSourceController(options: {
    onChange: () => void;
    onResolved: (deck: MarvelCdbDeckData) => string | null;
}): DeckSourceController {
    const sourceInputs = document.querySelectorAll<HTMLInputElement>('input[name="deck-source"]');
    const panel = document.querySelector<HTMLElement>('#marvelcdb-panel')!;
    const input = document.querySelector<HTMLInputElement>('#marvelcdb-reference')!;
    const loadButton = document.querySelector<HTMLButtonElement>('#marvelcdb-load')!;
    const status = document.querySelector<HTMLElement>('#marvelcdb-deck-status')!;
    const recentList = document.querySelector<HTMLElement>('#marvelcdb-recent')!;

    let source: 'precon' | 'marvelcdb' = 'precon';
    let deck: MarvelCdbDeckData | null = null;
    let busy = false;

    function clear(): void {
        deck = null;
        status.textContent = '';
        status.classList.remove('error');
    }

    function setSource(next: 'precon' | 'marvelcdb'): void {
        source = next;
        panel.hidden = next !== 'marvelcdb';
        if (next === 'precon') {
            clear();
        }
        options.onChange();
    }

    function renderRecent(): void {
        const recents = loadRecentDecks();
        recentList.replaceChildren();
        recentList.hidden = recents.length === 0;

        for (const recent of recents) {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'recent-deck';
            button.textContent = recent.name;
            button.title = `${recent.hero} — ${recent.reference}`;
            button.addEventListener('click', () => {
                input.value = recent.reference;
                void load();
            });
            recentList.appendChild(button);
        }
    }

    async function load(): Promise<void> {
        const reference = input.value.trim();
        if (!reference || busy) {
            return;
        }

        busy = true;
        status.classList.remove('error');
        status.textContent = 'Loading deck…';
        loadButton.disabled = true;
        options.onChange();

        try {
            const resolved = await resolveMarvelCdbDeck(reference);
            deck = resolved;
            status.textContent = options.onResolved(resolved)
                ?? (resolved.deck_name ?? resolved.name);
            rememberRecentDeck({
                reference,
                name: resolved.deck_name ?? resolved.name,
                hero: resolved.name,
            });
            renderRecent();
        } catch (error) {
            deck = null;
            status.classList.add('error');
            status.textContent = error instanceof Error
                ? error.message
                : 'Could not load that deck.';
        } finally {
            busy = false;
            loadButton.disabled = false;
            options.onChange();
        }
    }

    sourceInputs.forEach((element) => {
        element.addEventListener('change', () => {
            if (element.checked) {
                setSource(element.value === 'marvelcdb' ? 'marvelcdb' : 'precon');
            }
        });
    });
    loadButton.addEventListener('click', () => void load());
    input.addEventListener('keydown', (event) => {
        if (event.key === 'Enter') {
            event.preventDefault();
            void load();
        }
    });

    renderRecent();
    setSource('precon');

    return {
        getSource: () => source,
        getDeck: () => deck,
        isBusy: () => busy,
        clear,
        setDeck(next: MarvelCdbDeckData, notice: string) {
            deck = next;
            status.classList.remove('error');
            status.textContent = notice;
        },
    };
}
