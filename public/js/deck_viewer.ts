import { withCardImageRevision } from './card_image_url.js';

type DeckData = {
    name: string;
    deck_name?: string;
    hero: string[];
    hero_deck: string[];
    player_deck: string[];
    set_aside?: string[];
    obligations?: string[];
    nemesis_set?: string[];
};

type CardPaper = {
    card_id: string;
    pic_id?: string;
    type: string;
    name: string;
    subtitle?: string;
    desc: Record<string, string>;
    traits: string[];
    pack?: string;
};

type SetInfo = {
    name: string;
    heroes?: string[];
    scenarios?: string[];
};

type ProductInfo = {
    name: string;
    category: string;
};

type DeckChoice = {
    id: string;
    data: DeckData;
    isUserDeck: boolean;
};

type CardEntry = {
    key: string;
    cardIds: string[];
    cardId: string;
    quantity: number;
    paper: CardPaper;
};

const selectedDeckStorageKey = 'marvel_lcg_deck_viewer_deck';
const quickGameDeckStorageKey = 'marvel_lcg_solo_hero';

const deckSelect = document.querySelector<HTMLSelectElement>('#deck-select')!;
const deckStatus = document.querySelector<HTMLElement>('#deck-status')!;
const deckSourceBadge = document.querySelector<HTMLElement>('#deck-source-badge')!;
const deckSummary = document.querySelector<HTMLElement>('#deck-summary')!;
const deckContent = document.querySelector<HTMLElement>('#deck-content')!;
const identityImage = document.querySelector<HTMLImageElement>('#identity-image')!;
const deckHero = document.querySelector<HTMLElement>('#deck-hero')!;
const deckName = document.querySelector<HTMLElement>('#deck-name')!;
const deckCount = document.querySelector<HTMLElement>('#deck-count')!;
const deckAspects = document.querySelector<HTMLElement>('#deck-aspects')!;
const shareDeckButton = document.querySelector<HTMLButtonElement>('#share-deck')!;
const shareStatus = document.querySelector<HTMLElement>('#share-status')!;
const identityCards = document.querySelector<HTMLElement>('#identity-cards')!;
const signatureCards = document.querySelector<HTMLElement>('#signature-cards')!;
const playerCards = document.querySelector<HTMLElement>('#player-cards')!;
const encounterCards = document.querySelector<HTMLElement>('#encounter-cards')!;
const signatureCount = document.querySelector<HTMLElement>('#signature-count')!;
const playerCount = document.querySelector<HTMLElement>('#player-count')!;
const encounterCount = document.querySelector<HTMLElement>('#encounter-count')!;
const encounterSection = document.querySelector<HTMLDetailsElement>('#encounter-section')!;
const preview = document.querySelector<HTMLDialogElement>('#card-preview')!;
const previewImage = document.querySelector<HTMLImageElement>('#preview-image')!;
const previewName = document.querySelector<HTMLElement>('#preview-name')!;
const previewMeta = document.querySelector<HTMLElement>('#preview-meta')!;
const previewClose = document.querySelector<HTMLButtonElement>('#preview-close')!;
const previewFlip = document.querySelector<HTMLButtonElement>('#preview-flip')!;

const paperCache = new Map<string, Promise<CardPaper>>();
const productsByPack = new Map<string, ProductInfo>();
let choices: DeckChoice[] = [];
let previewFaces: string[] = [];
let previewFaceIndex = 0;
let currentDeck: DeckChoice | null = null;
let currentShareEntries: CardEntry[] = [];
let isCreatingShareImage = false;

function getFileName(path: string): string {
    return path.replace(/^.*[\\/]/, '').replace(/\.[^/.]+$/, '');
}

function splitCardIds(value: string): string[] {
    return value.split(',').map(id => id.trim()).filter(Boolean);
}

async function fetchJson<T>(url: string): Promise<T> {
    const response = await fetch(url);
    if (!response.ok) {
        throw new Error(`${response.status} ${response.statusText}`);
    }
    return await response.json() as T;
}

function getPaper(cardId: string): Promise<CardPaper> {
    const existing = paperCache.get(cardId);
    if (existing) {
        return existing;
    }
    const pending = fetchJson<CardPaper>(`/get_card_json?${encodeURIComponent(cardId)}`)
        .catch((error): CardPaper => {
            console.warn(`Failed to load card metadata ${cardId}`, error);
            return {
                card_id: cardId,
                type: 'Card',
                name: cardId,
                desc: {},
                traits: [],
            };
        });
    paperCache.set(cardId, pending);
    return pending;
}

async function loadChoices(): Promise<DeckChoice[]> {
    const [userPaths, starterPaths] = await Promise.all([
        fetchJson<string[]>('/list_user_deck?'),
        fetchJson<string[]>('/list_starter_deck?'),
    ]);
    const paths = [
        ...userPaths.map(path => ({path, isUserDeck: true})),
        ...starterPaths.map(path => ({path, isUserDeck: false})),
    ];
    const loaded = await Promise.all(paths.map(async ({path, isUserDeck}): Promise<DeckChoice | null> => {
        const id = getFileName(path);
        try {
            const data = await fetchJson<DeckData>(`/get_hero_json?${encodeURIComponent(id)}`);
            return {id, data, isUserDeck};
        } catch (error) {
            console.warn(`Failed to load deck ${id}`, error);
            return null;
        }
    }));
    return loaded.filter((choice): choice is DeckChoice => choice !== null);
}

function loadProductCatalog(sets: Record<string, SetInfo>): void {
    productsByPack.clear();
    for (const [label, info] of Object.entries(sets)) {
        if (!info?.name) {
            continue;
        }
        const match = label.match(/^(\d+)\.\s*(.+)$/);
        const order = match ? Number(match[1]) : 0;
        const productName = match?.[2] ?? label;
        const hasHeroes = (info.heroes?.length ?? 0) > 0;
        const hasScenarios = (info.scenarios?.length ?? 0) > 0;
        let category = 'Product';
        if (order === 1 || info.name === 'core') {
            category = 'Core Set';
        } else if (hasHeroes && hasScenarios) {
            category = 'Expansion';
        } else if (hasHeroes) {
            category = 'Hero Pack';
        } else if (hasScenarios) {
            category = 'Scenario Pack';
        }
        productsByPack.set(info.name, {name: productName, category});
    }
}

function fillDeckSelect(): void {
    deckSelect.replaceChildren();
    const groups: Array<{label: string; userDecks: boolean}> = [
        {label: 'My decks', userDecks: true},
        {label: 'Starter decks', userDecks: false},
    ];
    for (const groupInfo of groups) {
        const groupChoices = choices
            .filter(choice => choice.isUserDeck === groupInfo.userDecks)
            .sort((left, right) => (left.data.deck_name ?? left.data.name)
                .localeCompare(right.data.deck_name ?? right.data.name));
        if (!groupChoices.length) {
            continue;
        }
        const group = document.createElement('optgroup');
        group.label = groupInfo.label;
        for (const choice of groupChoices) {
            const option = document.createElement('option');
            option.value = choice.id;
            option.textContent = choice.data.deck_name ?? choice.data.name;
            group.appendChild(option);
        }
        deckSelect.appendChild(group);
    }
    deckSelect.disabled = choices.length === 0;
}

async function buildEntries(cardValues: string[]): Promise<CardEntry[]> {
    const grouped = new Map<string, {cardIds: string[]; quantity: number}>();
    for (const value of cardValues) {
        const cardIds = splitCardIds(value);
        const cardId = cardIds[0];
        if (!cardId) {
            continue;
        }
        const key = cardIds.join(',');
        const current = grouped.get(key);
        if (current) {
            current.quantity += 1;
        } else {
            grouped.set(key, {cardIds, quantity: 1});
        }
    }

    const entries = await Promise.all(Array.from(grouped, async ([key, value]): Promise<CardEntry> => ({
        key,
        cardIds: value.cardIds,
        cardId: value.cardIds[0],
        quantity: value.quantity,
        paper: await getPaper(value.cardIds[0]),
    })));
    return entries.sort((left, right) => {
        const typeComparison = left.paper.type.localeCompare(right.paper.type);
        return typeComparison || left.paper.name.localeCompare(right.paper.name);
    });
}

function cardMeta(paper: CardPaper): string {
    const parts = [paper.type];
    if (paper.desc.Cost !== undefined) {
        parts.push(`Cost ${paper.desc.Cost}`);
    }
    return parts.join(' · ');
}

function cardProduct(paper: CardPaper): string {
    const product = paper.pack ? productsByPack.get(paper.pack) : undefined;
    if (product) {
        return product.category === 'Core Set'
            ? product.name
            : `${product.name} · ${product.category}`;
    }
    return paper.pack ? `${paper.pack} · Product` : 'Product unavailable';
}

function sanitizeFileName(value: string): string {
    const cleaned = value
        .normalize('NFKD')
        .replace(/[^a-zA-Z0-9 _-]/g, '')
        .trim()
        .replace(/[ _]+/g, '-');
    return cleaned || 'marvel-champions-deck';
}

function loadCardImage(cardId: string): Promise<HTMLImageElement> {
    return new Promise((resolve, reject) => {
        const image = new Image();
        image.decoding = 'async';
        image.onload = () => resolve(image);
        image.onerror = () => reject(new Error(`Could not load card image ${cardId}`));
        image.src = withCardImageRevision(`/${cardId}`);
    });
}

function canvasToBlob(canvas: HTMLCanvasElement): Promise<Blob> {
    return new Promise((resolve, reject) => {
        canvas.toBlob((blob) => {
            if (blob) {
                resolve(blob);
            } else {
                reject(new Error('The browser could not create a PNG image.'));
            }
        }, 'image/png');
    });
}

function drawQuantity(
    context: CanvasRenderingContext2D,
    quantity: number,
    left: number,
    top: number,
    cardWidth: number,
): void {
    const radius = Math.round(cardWidth * 0.095);
    const centerX = left + cardWidth - radius - Math.round(cardWidth * 0.035);
    const centerY = top + radius + Math.round(cardWidth * 0.035);
    context.save();
    context.beginPath();
    context.arc(centerX, centerY, radius, 0, Math.PI * 2);
    context.fillStyle = 'rgba(5, 10, 16, 0.94)';
    context.fill();
    context.lineWidth = Math.max(3, Math.round(cardWidth * 0.012));
    context.strokeStyle = '#f4ca58';
    context.stroke();
    context.fillStyle = '#ffffff';
    context.font = `900 ${Math.round(cardWidth * 0.105)}px Arial, sans-serif`;
    context.textAlign = 'center';
    context.textBaseline = 'middle';
    context.shadowColor = '#000000';
    context.shadowBlur = 4;
    context.fillText(`×${quantity}`, centerX, centerY + 1);
    context.restore();
}

async function createShareImage(): Promise<void> {
    if (isCreatingShareImage || !currentDeck || !currentShareEntries.length) {
        return;
    }
    isCreatingShareImage = true;
    shareDeckButton.disabled = true;
    shareDeckButton.textContent = 'Creating PNG…';
    shareStatus.textContent = 'Loading card images…';

    try {
        const images = await Promise.all(currentShareEntries.map(entry => loadCardImage(entry.cardId)));
        const columns = currentShareEntries.length <= 12 ? 4 : 5;
        const cardWidth = 300;
        const cardHeight = 420;
        const gap = 10;
        const padding = 16;
        const rows = Math.ceil(currentShareEntries.length / columns);
        const canvas = document.createElement('canvas');
        canvas.width = padding * 2 + columns * cardWidth + (columns - 1) * gap;
        canvas.height = padding * 2 + rows * cardHeight + (rows - 1) * gap;
        const context = canvas.getContext('2d');
        if (!context) {
            throw new Error('Canvas is not available in this browser.');
        }

        context.fillStyle = '#09121a';
        context.fillRect(0, 0, canvas.width, canvas.height);
        images.forEach((image, index) => {
            const column = index % columns;
            const row = Math.floor(index / columns);
            const left = padding + column * (cardWidth + gap);
            const top = padding + row * (cardHeight + gap);
            context.drawImage(image, left, top, cardWidth, cardHeight);
            drawQuantity(context, currentShareEntries[index].quantity, left, top, cardWidth);
        });

        shareStatus.textContent = 'Saving image…';
        const blob = await canvasToBlob(canvas);
        const objectUrl = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = objectUrl;
        link.download = `${sanitizeFileName(currentDeck.data.deck_name ?? currentDeck.data.name)}.png`;
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
        shareStatus.textContent = 'PNG saved to your Downloads.';
    } catch (error) {
        console.error(error);
        shareStatus.textContent = error instanceof Error
            ? error.message
            : 'Could not create the deck image.';
    } finally {
        isCreatingShareImage = false;
        shareDeckButton.disabled = false;
        shareDeckButton.textContent = 'Share Deck';
    }
}

function openPreview(entry: CardEntry): void {
    previewFaces = entry.cardIds;
    previewFaceIndex = 0;
    previewImage.src = withCardImageRevision(`/${previewFaces[0]}`);
    previewImage.alt = entry.paper.name;
    previewName.textContent = entry.paper.name;
    previewMeta.textContent = `${cardMeta(entry.paper)} · ${cardProduct(entry.paper)}`;
    previewFlip.hidden = previewFaces.length < 2;
    preview.showModal();
}

function createCardTile(entry: CardEntry): HTMLButtonElement {
    const tile = document.createElement('button');
    tile.type = 'button';
    tile.className = 'card-tile';
    tile.title = `Preview ${entry.paper.name}`;

    const image = document.createElement('img');
    image.src = withCardImageRevision(`/${entry.cardId}`);
    image.alt = entry.paper.name;
    image.loading = 'lazy';

    if (entry.quantity > 1) {
        const quantity = document.createElement('span');
        quantity.className = 'card-quantity';
        quantity.textContent = `×${entry.quantity}`;
        tile.appendChild(quantity);
    }

    const name = document.createElement('span');
    name.className = 'card-name';
    name.textContent = entry.paper.name;

    const meta = document.createElement('span');
    meta.className = 'card-meta';
    meta.textContent = cardMeta(entry.paper);

    const product = document.createElement('span');
    product.className = 'card-product';
    product.textContent = cardProduct(entry.paper);

    tile.append(image, name, meta, product);
    tile.addEventListener('click', () => openPreview(entry));
    return tile;
}

function renderEntries(container: HTMLElement, entries: CardEntry[]): void {
    container.replaceChildren(...entries.map(createCardTile));
}

async function showDeck(choice: DeckChoice): Promise<void> {
    deckStatus.textContent = 'Loading cards…';
    shareStatus.textContent = '';
    deckSelect.disabled = true;
    localStorage.setItem(selectedDeckStorageKey, choice.id);
    const url = new URL(window.location.href);
    url.searchParams.set('deck', choice.id);
    window.history.replaceState({}, '', url);

    try {
        const related = [
            ...(choice.data.set_aside ?? []),
            ...(choice.data.obligations ?? []),
            ...(choice.data.nemesis_set ?? []),
        ];
        const [identities, signatures, playerDeck, relatedCards] = await Promise.all([
            buildEntries(choice.data.hero ?? []),
            buildEntries(choice.data.hero_deck ?? []),
            buildEntries(choice.data.player_deck ?? []),
            buildEntries(related),
        ]);
        currentDeck = choice;
        currentShareEntries = [...identities, ...signatures, ...playerDeck];

        renderEntries(identityCards, identities);
        renderEntries(signatureCards, signatures);
        renderEntries(playerCards, playerDeck);
        renderEntries(encounterCards, relatedCards);

        const identity = identities[0];
        identityImage.src = identity
            ? withCardImageRevision(`/${identity.cardId}`)
            : '/player';
        identityImage.alt = choice.data.name;
        deckHero.textContent = choice.data.name;
        deckName.textContent = choice.data.deck_name ?? `${choice.data.name} Starter Deck`;
        const constructedSize = choice.data.hero_deck.length + choice.data.player_deck.length;
        deckCount.textContent = `${constructedSize} cards · ${choice.data.hero_deck.length} signature · ${choice.data.player_deck.length} aspect/basic`;
        signatureCount.textContent = `${choice.data.hero_deck.length} cards`;
        playerCount.textContent = `${choice.data.player_deck.length} cards`;
        encounterCount.textContent = `${related.length} cards`;
        encounterSection.hidden = related.length === 0;

        const aspects = Array.from(new Set(playerDeck
            .map(entry => entry.paper.desc.Class)
            .filter((value): value is string => Boolean(value))));
        deckAspects.replaceChildren(...aspects.map(aspect => {
            const badge = document.createElement('span');
            badge.textContent = aspect;
            return badge;
        }));

        deckSourceBadge.hidden = false;
        deckSourceBadge.textContent = choice.isUserDeck ? 'MY DECK' : 'STARTER DECK';
        deckSourceBadge.classList.toggle('starter', !choice.isUserDeck);
        deckSummary.hidden = false;
        deckContent.hidden = false;
        deckStatus.textContent = '';
    } catch (error) {
        console.error(error);
        deckStatus.textContent = 'Could not load all cards in this deck.';
        deckSummary.hidden = true;
        deckContent.hidden = true;
        currentDeck = null;
        currentShareEntries = [];
    } finally {
        deckSelect.disabled = choices.length === 0;
    }
}

deckSelect.addEventListener('change', () => {
    const choice = choices.find(item => item.id === deckSelect.value);
    if (choice) {
        void showDeck(choice);
    }
});

shareDeckButton.addEventListener('click', () => {
    void createShareImage();
});

previewClose.addEventListener('click', () => preview.close());
preview.addEventListener('click', (event) => {
    if (event.target === preview) {
        preview.close();
    }
});
previewFlip.addEventListener('click', () => {
    previewFaceIndex = (previewFaceIndex + 1) % previewFaces.length;
    previewImage.src = withCardImageRevision(`/${previewFaces[previewFaceIndex]}`);
});

async function initialize(): Promise<void> {
    try {
        const [loadedChoices, sets] = await Promise.all([
            loadChoices(),
            fetchJson<Record<string, SetInfo>>('/get_sets_json?'),
        ]);
        choices = loadedChoices;
        loadProductCatalog(sets);
        fillDeckSelect();
        if (!choices.length) {
            deckStatus.textContent = 'No local decks are available.';
            return;
        }
        const requestedId = new URLSearchParams(window.location.search).get('deck');
        const savedId = localStorage.getItem(selectedDeckStorageKey);
        const quickGameDeckId = localStorage.getItem(quickGameDeckStorageKey);
        const selected = choices.find(choice => choice.id === requestedId)
            ?? choices.find(choice => choice.id === savedId)
            ?? choices.find(choice => choice.id === quickGameDeckId)
            ?? choices.find(choice => choice.isUserDeck)
            ?? choices[0];
        deckSelect.value = selected.id;
        await showDeck(selected);
    } catch (error) {
        console.error(error);
        deckStatus.textContent = 'Could not load local decks.';
        deckSelect.replaceChildren();
        deckSelect.disabled = true;
    }
}

void initialize();
