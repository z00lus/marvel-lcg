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
    text?: string;
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
    const response = await fetch(url, {cache: 'no-store'});
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
            .filter(choice => choice.isUserDeck === groupInfo.userDecks);
        if (!groupInfo.userDecks) {
            groupChoices.sort((left, right) =>
                (left.data.deck_name ?? left.data.name)
                    .localeCompare(right.data.deck_name ?? right.data.name));
        }
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

async function showDeck(choice: DeckChoice, resetEditor = true): Promise<void> {
    deckStatus.textContent = 'Loading cards…';
    shareStatus.textContent = '';
    deckSelect.disabled = true;
    localStorage.setItem(selectedDeckStorageKey, choice.id);
    const url = new URL(window.location.href);
    url.searchParams.set('deck', choice.id);
    window.history.replaceState({}, '', url);

    try {
        if (resetEditor) {
            choice = await loadEditor(choice);
        }
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
        renderEditableCards(playerDeck);
        renderEntries(encounterCards, relatedCards);

        const identity = identities[0];
        identityImage.src = identity
            ? withCardImageRevision(`/${identity.cardId}`)
            : '/player';
        identityImage.alt = choice.data.name;
        deckHero.textContent = choice.data.name;
        deckName.textContent = choice.data.deck_name ?? `${choice.data.name} Starter Deck`;
        const constructedSize = validation?.size ?? choice.data.hero_deck.length + choice.data.player_deck.length;
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
        renderEditor();
    } catch (error) {
        console.error(error);
        deckStatus.textContent = error instanceof Error ? error.message : 'Could not load this deck.';
        editorControls.hidden = true;
        catalogSection.hidden = true;
        deckSummary.hidden = true;
        deckContent.hidden = true;
        currentDeck = null;
        currentShareEntries = [];
    } finally {
        deckSelect.disabled = choices.length === 0;
    }
}

deckSelect.addEventListener('change', () => {
    if (dirty && !window.confirm('Discard your unsaved deck changes?')) {
        deckSelect.value = sourceDeck?.id ?? '';
        return;
    }
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



type DeckValidation = {
    legal: boolean;
    issues: string[];
    size: number;
    aspect_counts: Record<string, number>;
    blocked: Record<string, string>;
};
type EditorLoad = {
    deck: DeckData;
    aspects: string[];
    aspect_count: number;
    revision: string;
    copy_on_save: boolean;
    catalog: CardPaper[];
    validation: DeckValidation;
};
const aspectNames = ['Aggression', 'Justice', 'Leadership', 'Protection', "'Pool"];
const editorControls = document.querySelector<HTMLElement>('#editor-controls')!;
const nameInput = document.querySelector<HTMLInputElement>('#edit-deck-name')!;
const aspectInputs = document.querySelector<HTMLFieldSetElement>('#edit-aspects')!;
const editorNote = document.querySelector<HTMLElement>('#editor-note')!;
const editorStatus = document.querySelector<HTMLElement>('#editor-status')!;
const validationBox = document.querySelector<HTMLElement>('#deck-validation')!;
const saveButton = document.querySelector<HTMLButtonElement>('#save-deck')!;
const discardButton = document.querySelector<HTMLButtonElement>('#discard-changes')!;
const catalogSection = document.querySelector<HTMLElement>('#card-catalog')!;
const catalogCards = document.querySelector<HTMLElement>('#catalog-cards')!;
const catalogStatus = document.querySelector<HTMLElement>('#catalog-status')!;
const searchInput = document.querySelector<HTMLInputElement>('#card-search')!;
const aspectFilter = document.querySelector<HTMLSelectElement>('#filter-aspect')!;
const typeFilter = document.querySelector<HTMLSelectElement>('#filter-type')!;
const costFilter = document.querySelector<HTMLSelectElement>('#filter-cost')!;
const availableFilter = document.querySelector<HTMLInputElement>('#filter-available')!;
const moreButton = document.querySelector<HTMLButtonElement>('#catalog-more')!;
let sourceDeck: DeckChoice | null = null;
let catalog: CardPaper[] = [];
let aspects: string[] = [];
let aspectCount = 1;
let revision = '';
let copyOnSave = true;
let validation: DeckValidation | null = null;
let dirty = false;
let busy = false;
let catalogLimit = 36;

async function editorRequest<T>(action: string, extra: Record<string, unknown> = {}): Promise<T> {
    if (!sourceDeck) throw new Error('Choose a deck first.');
    const response = await fetch('/deck_editor', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({action, source: sourceDeck.isUserDeck ? 'user' : 'starter', id: sourceDeck.id, ...extra}),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error ?? 'The deck could not be updated.');
    return data as T;
}

function fillFilter(select: HTMLSelectElement, values: string[]): void {
    const first = select.options[0];
    select.replaceChildren(first);
    for (const value of values) select.add(new Option(value, value));
}

async function loadEditor(choice: DeckChoice): Promise<DeckChoice> {
    sourceDeck = choice;
    busy = true;
    editorControls.hidden = true;
    catalogSection.hidden = true;
    try {
        const loaded = await editorRequest<EditorLoad>('load');
        catalog = loaded.catalog.sort((a, b) => a.name.localeCompare(b.name));
        for (const paper of catalog) paperCache.set(paper.card_id, Promise.resolve(paper));
        aspects = loaded.aspects;
        aspectCount = loaded.aspect_count;
        revision = loaded.revision;
        copyOnSave = loaded.copy_on_save;
        validation = loaded.validation;
        dirty = false;
        nameInput.value = loaded.deck.deck_name ?? loaded.deck.name;
        if (copyOnSave) nameInput.value += ' — Custom';
        loaded.deck.deck_name = nameInput.value;
        editorStatus.textContent = '';
        searchInput.value = '';
        availableFilter.checked = true;
        fillFilter(aspectFilter, [...aspectNames, 'Basic']);
        fillFilter(typeFilter, [...new Set(catalog.map(p => p.type))].sort());
        fillFilter(costFilter, [...new Set(catalog.map(p => p.desc.Cost).filter(v => v !== undefined))].sort());
        catalogLimit = 36;
        return {...choice, data: loaded.deck};
    } finally {
        busy = false;
    }
}

function setBusy(value: boolean): void {
    busy = value;
    deckSelect.disabled = value;
    nameInput.disabled = value;
    aspectInputs.disabled = value;
    discardButton.disabled = value || !dirty;
    updateSaveButton();
    for (const button of document.querySelectorAll<HTMLButtonElement>('.card-controls button')) {
        button.disabled = value || button.dataset.blocked === 'true';
    }
}

function updateSaveButton(): void {
    saveButton.disabled = busy || !validation?.legal || !nameInput.value.trim();
    saveButton.textContent = copyOnSave ? 'Save as new deck' : 'Save changes';
}

function renderEditor(): void {
    editorControls.hidden = false;
    catalogSection.hidden = false;
    editorNote.textContent = copyOnSave
        ? 'Saving creates your own local copy. The original deck stays unchanged.'
        : 'This is your local deck. Saved changes are available in Quick Game and Campaign.';
    aspectInputs.replaceChildren();
    const legend = document.createElement('legend');
    legend.textContent = `Choose ${aspectCount} aspect${aspectCount === 1 ? '' : 's'}`;
    aspectInputs.append(legend);
    for (const aspect of aspectNames) {
        const label = document.createElement('label');
        const input = document.createElement('input');
        input.type = 'checkbox';
        input.checked = aspects.includes(aspect);
        input.disabled = !input.checked && aspects.length >= aspectCount && aspectCount !== 1;
        input.addEventListener('change', () => {
            const next = aspectCount === 1 ? [aspect] : input.checked
                ? [...aspects, aspect] : aspects.filter(a => a !== aspect);
            void changeDraft(currentDeck!.data.player_deck, next);
        });
        label.append(input, document.createTextNode(aspect));
        aspectInputs.append(label);
    }
    validationBox.replaceChildren();
    validationBox.classList.toggle('valid', validation?.legal ?? false);
    if (validation?.legal) {
        validationBox.textContent = `Legal deck · ${validation.size}/50 cards · Rules Reference 1.8`;
    } else {
        const heading = document.createElement('p');
        heading.textContent = 'Finish these changes before saving:';
        const list = document.createElement('ul');
        for (const issue of validation?.issues ?? []) {
            const item = document.createElement('li');
            item.textContent = issue;
            list.append(item);
        }
        validationBox.append(heading, list);
    }
    renderCatalog();
    setBusy(busy);
}

function controlButton(text: string, label: string, action: () => void, reason = ''): HTMLButtonElement {
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = text;
    button.setAttribute('aria-label', label);
    button.title = reason || label;
    button.dataset.blocked = String(Boolean(reason));
    button.disabled = busy || Boolean(reason);
    button.addEventListener('click', action);
    return button;
}

function editableTile(entry: CardEntry, inDeck: boolean): HTMLElement {
    const wrapper = document.createElement('div');
    wrapper.className = 'editable-card';
    wrapper.dataset.cardId = entry.cardId;
    wrapper.append(createCardTile(entry));
    const controls = document.createElement('div');
    controls.className = 'card-controls';
    if (inDeck) {
        const quantity = document.createElement('span');
        quantity.textContent = String(entry.quantity);
        quantity.setAttribute('aria-label', `${entry.quantity} copies`);
        controls.append(controlButton('−', `Remove one ${entry.paper.name}`, () => editCount(entry.key, -1)), quantity);
    }
    const reason = validation?.blocked[entry.cardId] ?? 'This card cannot be added.';
    controls.append(controlButton(inDeck ? '+' : 'Add card', `Add ${entry.paper.name}`, () => editCount(entry.key, 1), reason));
    if (inDeck) {
        const remove = controlButton('Remove', `Remove all ${entry.paper.name}`, () => editCount(entry.key, -entry.quantity));
        remove.className = 'remove-card';
        controls.append(remove);
    }
    wrapper.append(controls);
    if (reason && !inDeck) {
        const explanation = document.createElement('p');
        explanation.className = 'card-blocked';
        explanation.textContent = reason;
        wrapper.append(explanation);
    }
    return wrapper;
}

function renderEditableCards(entries: CardEntry[]): void {
    playerCards.replaceChildren(...entries.map(entry => editableTile(entry, true)));
}

function editCount(card: string, difference: number): void {
    if (busy || !currentDeck) return;
    const next = [...currentDeck.data.player_deck];
    if (difference > 0) {
        if (validation?.blocked[card] !== '') return;
        next.push(card);
    } else {
        for (let i = 0; i < -difference; i++) {
            const index = next.indexOf(card);
            if (index >= 0) next.splice(index, 1);
        }
    }
    void changeDraft(next, aspects);
}

async function changeDraft(cards: string[], nextAspects: string[]): Promise<void> {
    if (busy || !currentDeck) return;
    setBusy(true);
    editorStatus.textContent = 'Checking deck…';
    try {
        validation = await editorRequest<DeckValidation>('validate', {player_deck: cards, aspects: nextAspects});
        currentDeck.data.player_deck = [...cards];
        aspects = [...nextAspects];
        dirty = true;
        await showDeck(currentDeck, false);
        editorStatus.textContent = 'Unsaved changes';
    } catch (error) {
        editorStatus.textContent = error instanceof Error ? error.message : 'Could not check deck.';
        renderEditor();
    } finally {
        setBusy(false);
    }
}

function normalizeSearch(value: string): string {
    return value.normalize('NFKD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
}

function renderCatalog(): void {
    const terms = normalizeSearch(searchInput.value).split(/\s+/).filter(Boolean);
    const results = catalog.filter(paper => {
        if (aspectFilter.value && !paper.desc.Class.split(';').includes(aspectFilter.value)) return false;
        if (typeFilter.value && paper.type !== typeFilter.value) return false;
        if (costFilter.value && paper.desc.Cost !== costFilter.value) return false;
        if (availableFilter.checked && validation?.blocked[paper.card_id]) return false;
        const text = normalizeSearch([paper.name, paper.subtitle, paper.card_id, paper.text?.replace(/<[^>]*>/g, ''),
            ...paper.traits, cardProduct(paper)].join(' '));
        return terms.every(term => text.includes(term));
    });
    catalogStatus.textContent = results.length
        ? `${results.length} cards found · showing ${Math.min(catalogLimit, results.length)}`
        : 'No matching cards. Try a shorter search or change the filters.';
    catalogCards.replaceChildren(...results.slice(0, catalogLimit).map(paper => editableTile({
        key: paper.card_id, cardIds: [paper.card_id], cardId: paper.card_id, quantity: 1, paper,
    }, false)));
    moreButton.hidden = results.length <= catalogLimit;
}

for (const input of [searchInput, aspectFilter, typeFilter, costFilter, availableFilter]) {
    input.addEventListener('input', () => { catalogLimit = 36; renderCatalog(); });
}
moreButton.addEventListener('click', () => { catalogLimit += 36; renderCatalog(); });
nameInput.addEventListener('input', () => {
    if (currentDeck) currentDeck.data.deck_name = nameInput.value;
    deckName.textContent = nameInput.value;
    dirty = true;
    editorStatus.textContent = 'Unsaved changes';
    discardButton.disabled = false;
    updateSaveButton();
});
discardButton.addEventListener('click', () => {
    if (!busy && sourceDeck) void showDeck(sourceDeck);
});
window.addEventListener('beforeunload', event => {
    if (dirty) { event.preventDefault(); event.returnValue = ''; }
});
saveButton.addEventListener('click', async () => {
    if (busy || !currentDeck || !validation?.legal) return;
    setBusy(true);
    editorStatus.textContent = 'Saving…';
    try {
        const saved = await editorRequest<{id: string; deck: DeckData; revision: string}>('save', {
            player_deck: currentDeck.data.player_deck, aspects, name: nameInput.value, revision,
        });
        const choice: DeckChoice = {id: saved.id, data: saved.deck, isUserDeck: true};
        choices = [choice, ...choices.filter(item => item.id !== saved.id)];
        fillDeckSelect();
        deckSelect.value = saved.id;
        await showDeck(choice);
        editorStatus.textContent = 'Deck saved. It is ready to select in Quick Game or Campaign.';
    } catch (error) {
        editorStatus.textContent = error instanceof Error ? error.message : 'Could not save deck.';
    } finally {
        setBusy(false);
    }
});

void initialize();
