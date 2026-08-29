import { withCardImageRevision } from './card_image_url.js';

type SetInfo = {
    scenarios: string[];
    heroes: string[];
    out_of_print?: boolean;
};

type HeroData = {
    name: string;
    deck_name?: string;
    hero: string[];
};

type ScenarioData = {
    name: string;
    villain?: string[];
    schemes?: string[];
    underling_sets?: string[];
};

type UnderlingData = {
    name: string;
    villain?: string[];
};

type HeroChoice = {
    id: string;
    name: string;
    imageId: string;
    isUserDeck: boolean;
};

type ScenarioChoice = {
    id: string;
    name: string;
    imageId: string;
    data: ScenarioData;
};

type UnderlingChoice = {
    id: string;
    name: string;
    imageId: string;
};

type ProxyKind = 'hero' | 'scenario';

const heroStorageKey = 'marvel_lcg_proxy_hero';
const scenarioStorageKey = 'marvel_lcg_proxy_scenario';
const underlingStorageKey = 'marvel_lcg_proxy_underling';
const newScenarioIds = new Set([
    'kingpin', 'protection_racket', 'the_raft_breakout', 'art_museum_heist',
    'the_getaway', 'stop_the_presses',
]);
const newUnderlingIds = new Set([
    'bullseye', 'electro', 'hammerhead', 'purple_man', 'typhoid_mary',
]);
const newHeroIds = new Set(['echo', 'daredevil', 'jessica_jones']);

const heroKindButton = document.querySelector<HTMLButtonElement>('#hero-kind')!;
const scenarioKindButton = document.querySelector<HTMLButtonElement>('#scenario-kind')!;
const heroSection = document.querySelector<HTMLElement>('#hero-section')!;
const scenarioSection = document.querySelector<HTMLElement>('#scenario-section')!;
const underlingSection = document.querySelector<HTMLElement>('#underling-section')!;
const heroList = document.querySelector<HTMLElement>('#hero-list')!;
const scenarioList = document.querySelector<HTMLElement>('#scenario-list')!;
const underlingList = document.querySelector<HTMLElement>('#underling-list')!;
const heroStatus = document.querySelector<HTMLElement>('#hero-status')!;
const scenarioStatus = document.querySelector<HTMLElement>('#scenario-status')!;
const heroSelection = document.querySelector<HTMLElement>('#hero-selection')!;
const scenarioSelection = document.querySelector<HTMLElement>('#scenario-selection')!;
const underlingSelection = document.querySelector<HTMLElement>('#underling-selection')!;
const downloadButton = document.querySelector<HTMLButtonElement>('#download-button')!;
const errorMessage = document.querySelector<HTMLElement>('#error-message')!;
const resultMessage = document.querySelector<HTMLElement>('#result-message')!;

let currentKind: ProxyKind = 'hero';
let selectedHero: HeroChoice | null = null;
let selectedScenario: ScenarioChoice | null = null;
let selectedUnderling: UnderlingChoice | null = null;
let isGenerating = false;

function getFileName(path: string): string {
    return path.replace(/^.*[\\/]/, '').replace(/\.[^/.]+$/, '');
}

function getFirstCardId(cardIds: string[] | undefined): string {
    return cardIds?.[0]?.split(',')[0] ?? '';
}

async function fetchJson<T>(url: string): Promise<T> {
    const response = await fetch(url);
    if (!response.ok) {
        throw new Error(`${response.status} ${response.statusText}`);
    }
    return await response.json() as T;
}

function markSelected(container: HTMLElement, selectedId: string): void {
    container.querySelectorAll<HTMLButtonElement>('.choice-card').forEach((button) => {
        const selected = button.dataset.id === selectedId;
        button.classList.toggle('selected', selected);
        button.setAttribute('aria-pressed', selected.toString());
    });
}

function createChoiceButton(
    id: string,
    name: string,
    imageId: string,
    onSelect: () => void,
    options: {isNew?: boolean; isUserDeck?: boolean} = {},
): HTMLButtonElement {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'choice-card';
    button.dataset.id = id;
    button.setAttribute('aria-pressed', 'false');
    button.classList.toggle('new-content', options.isNew === true);
    button.classList.toggle('user-deck', options.isUserDeck === true);

    const image = document.createElement('img');
    image.src = withCardImageRevision(`/${imageId}`);
    image.alt = '';

    const title = document.createElement('span');
    title.className = 'choice-name';
    title.textContent = name;

    button.append(image, title);
    button.addEventListener('click', onSelect);
    return button;
}

function scenarioNeedsUnderling(): boolean {
    return (selectedScenario?.data.underling_sets?.length ?? 0) > 0;
}

function updateDownloadButton(): void {
    const selectionMissing = currentKind === 'hero'
        ? selectedHero === null
        : selectedScenario === null || (scenarioNeedsUnderling() && selectedUnderling === null);
    downloadButton.disabled = isGenerating || selectionMissing;
}

function setKind(kind: ProxyKind): void {
    currentKind = kind;
    const heroActive = kind === 'hero';
    heroKindButton.classList.toggle('active', heroActive);
    scenarioKindButton.classList.toggle('active', !heroActive);
    heroKindButton.setAttribute('aria-pressed', heroActive.toString());
    scenarioKindButton.setAttribute('aria-pressed', (!heroActive).toString());
    heroSection.hidden = !heroActive;
    scenarioSection.hidden = heroActive;
    underlingSection.hidden = heroActive || !scenarioNeedsUnderling();
    errorMessage.textContent = '';
    resultMessage.textContent = '';
    updateDownloadButton();
}

function selectHero(choice: HeroChoice): void {
    selectedHero = choice;
    localStorage.setItem(heroStorageKey, choice.id);
    heroSelection.textContent = choice.name;
    markSelected(heroList, choice.id);
    errorMessage.textContent = '';
    resultMessage.textContent = '';
    updateDownloadButton();
}

function selectUnderling(choice: UnderlingChoice): void {
    selectedUnderling = choice;
    localStorage.setItem(underlingStorageKey, choice.id);
    underlingSelection.textContent = choice.name;
    markSelected(underlingList, choice.id);
    errorMessage.textContent = '';
    resultMessage.textContent = '';
    updateDownloadButton();
}

async function loadUnderlings(ids: string[]): Promise<void> {
    const generation = ids.join('|');
    selectedUnderling = null;
    underlingList.replaceChildren();
    underlingSelection.textContent = 'Not selected';
    underlingSection.hidden = currentKind !== 'scenario' || ids.length === 0;
    updateDownloadButton();
    if (!ids.length) {
        return;
    }

    const choices = (await Promise.all(ids.map(async (id): Promise<UnderlingChoice | null> => {
        try {
            const data = await fetchJson<UnderlingData>(
                `/get_encounter_set_json?${encodeURIComponent(id)}`,
            );
            const imageId = getFirstCardId(data.villain);
            if (!data.name || !imageId) {
                return null;
            }
            return {id, name: data.name, imageId};
        } catch (error) {
            console.warn(`Failed to load underling ${id}`, error);
            return null;
        }
    }))).filter((choice): choice is UnderlingChoice => choice !== null);

    if (selectedScenario?.data.underling_sets?.join('|') !== generation) {
        return;
    }
    for (const choice of choices) {
        underlingList.appendChild(createChoiceButton(
            choice.id,
            choice.name,
            choice.imageId,
            () => selectUnderling(choice),
            {isNew: newUnderlingIds.has(choice.id)},
        ));
    }

    const savedId = localStorage.getItem(underlingStorageKey);
    const savedChoice = choices.find((choice) => choice.id === savedId) ?? choices[0];
    if (savedChoice) {
        selectUnderling(savedChoice);
    } else {
        errorMessage.textContent = 'No underlings are available for this scenario.';
    }
    updateDownloadButton();
}

function selectScenario(choice: ScenarioChoice): void {
    selectedScenario = choice;
    localStorage.setItem(scenarioStorageKey, choice.id);
    scenarioSelection.textContent = choice.name;
    markSelected(scenarioList, choice.id);
    errorMessage.textContent = '';
    resultMessage.textContent = '';
    void loadUnderlings(choice.data.underling_sets ?? []);
    updateDownloadButton();
}

async function loadHeroChoices(): Promise<HeroChoice[]> {
    const [starterPaths, userPaths, sets] = await Promise.all([
        fetchJson<string[]>('/list_starter_deck?'),
        fetchJson<string[]>('/list_user_deck?'),
        fetchJson<Record<string, SetInfo>>('/get_sets_json?'),
    ]);
    const outOfPrintHeroIds = new Set(
        Object.values(sets)
            .filter(set => set.out_of_print === true)
            .flatMap(set => set.heroes ?? []),
    );
    const paths = [
        ...userPaths.map(path => ({path, isUserDeck: true})),
        ...starterPaths.map(path => ({path, isUserDeck: false})),
    ];

    const choices = await Promise.all(paths.map(async ({path, isUserDeck}): Promise<HeroChoice | null> => {
        const id = getFileName(path);
        try {
            const data = await fetchJson<HeroData>(`/get_hero_json?${encodeURIComponent(id)}`);
            const imageId = getFirstCardId(data.hero);
            if (!data.name || !imageId) {
                return null;
            }
            return {
                id,
                name: data.deck_name ?? data.name,
                imageId,
                isUserDeck,
            };
        } catch (error) {
            console.warn(`Failed to load hero deck ${id}`, error);
            return null;
        }
    }));
    const loadedChoices = choices.filter((choice): choice is HeroChoice => choice !== null);
    const outOfPrintIdentityIds = new Set(
        loadedChoices
            .filter(choice => !choice.isUserDeck && outOfPrintHeroIds.has(choice.id))
            .map(choice => choice.imageId.toLowerCase()),
    );
    return loadedChoices.filter(choice =>
        outOfPrintHeroIds.has(choice.id)
        || outOfPrintIdentityIds.has(choice.imageId.toLowerCase()),
    );
}

async function loadScenarioChoices(): Promise<ScenarioChoice[]> {
    const [sets, availablePaths] = await Promise.all([
        fetchJson<Record<string, SetInfo>>('/get_sets_json?'),
        fetchJson<string[]>('/list_scenarios?'),
    ]);
    const availableIds = new Set(availablePaths.map(getFileName));
    const ids = Array.from(new Set(
        Object.entries(sets)
            .filter(([setName, set]) => /^\d+\./.test(setName) && set.out_of_print === true)
            .flatMap(([, set]) => set.scenarios ?? [])
            .filter(id => availableIds.has(id)),
    ));

    const choices = await Promise.all(ids.map(async (id): Promise<ScenarioChoice | null> => {
        try {
            const data = await fetchJson<ScenarioData>(
                `/get_scenario_json?${encodeURIComponent(id)}`,
            );
            const imageSource = (data.underling_sets?.length ?? 0) > 0
                ? data.schemes
                : (data.villain?.length ? data.villain : data.schemes);
            const imageId = getFirstCardId(imageSource);
            if (!data.name || !imageId) {
                return null;
            }
            return {id, name: data.name, imageId, data};
        } catch (error) {
            console.warn(`Failed to load scenario ${id}`, error);
            return null;
        }
    }));
    return choices.filter((choice): choice is ScenarioChoice => choice !== null);
}

function renderHeroes(choices: HeroChoice[]): void {
    heroList.replaceChildren();
    for (const choice of choices) {
        heroList.appendChild(createChoiceButton(
            choice.id,
            choice.name,
            choice.imageId,
            () => selectHero(choice),
            {
                isNew: !choice.isUserDeck && newHeroIds.has(choice.id),
                isUserDeck: choice.isUserDeck,
            },
        ));
    }
    const savedId = localStorage.getItem(heroStorageKey);
    const savedChoice = choices.find(choice => choice.id === savedId);
    if (savedChoice) {
        selectHero(savedChoice);
    }
    heroStatus.textContent = choices.length ? '' : 'No hero decks are available.';
}

function renderScenarios(choices: ScenarioChoice[]): void {
    scenarioList.replaceChildren();
    const ordered = [...choices].sort((left, right) =>
        Number(newScenarioIds.has(right.id)) - Number(newScenarioIds.has(left.id)),
    );
    for (const choice of ordered) {
        scenarioList.appendChild(createChoiceButton(
            choice.id,
            choice.name,
            choice.imageId,
            () => selectScenario(choice),
            {isNew: newScenarioIds.has(choice.id)},
        ));
    }
    const savedId = localStorage.getItem(scenarioStorageKey);
    const savedChoice = choices.find(choice => choice.id === savedId);
    if (savedChoice) {
        selectScenario(savedChoice);
    }
    scenarioStatus.textContent = choices.length ? '' : 'No scenarios are available.';
}

function downloadName(response: Response, fallback: string): string {
    const disposition = response.headers.get('Content-Disposition') ?? '';
    const encoded = disposition.match(/filename\*=UTF-8''([^;]+)/i)?.[1];
    if (!encoded) {
        return fallback;
    }
    try {
        return decodeURIComponent(encoded);
    } catch (_) {
        return fallback;
    }
}

async function generatePdf(): Promise<void> {
    if (isGenerating || downloadButton.disabled) {
        return;
    }
    const choice = currentKind === 'hero' ? selectedHero : selectedScenario;
    if (!choice) {
        return;
    }

    isGenerating = true;
    errorMessage.textContent = '';
    resultMessage.textContent = '';
    downloadButton.textContent = 'Generating PDF…';
    downloadButton.setAttribute('aria-busy', 'true');
    updateDownloadButton();

    try {
        const response = await fetch('/proxy/generate', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                kind: currentKind,
                id: choice.id,
                underling_id: currentKind === 'scenario' ? selectedUnderling?.id ?? '' : '',
            }),
        });
        if (!response.ok) {
            let message = `PDF generation failed (${response.status}).`;
            try {
                const payload = await response.json() as {error?: string};
                message = payload.error ?? message;
            } catch (_) {
                // Keep the HTTP fallback for a non-JSON error response.
            }
            throw new Error(message);
        }

        const blob = await response.blob();
        const fallbackName = `${choice.id}-${currentKind}-proxy.pdf`;
        const fileName = downloadName(response, fallbackName);
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = fileName;
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.setTimeout(() => URL.revokeObjectURL(url), 1000);

        const serverPath = response.headers.get('X-Proxy-Path') ?? './proxy-output/';
        const cards = response.headers.get('X-Proxy-Cards') ?? '?';
        const pages = response.headers.get('X-Proxy-Pages') ?? '?';
        resultMessage.textContent = (
            `Downloaded ${cards} card faces on ${pages} A4 pages. `
            + `A server copy is saved at ${serverPath}`
        );
    } catch (error) {
        console.error(error);
        errorMessage.textContent = error instanceof Error
            ? error.message
            : 'The proxy PDF could not be generated.';
    } finally {
        isGenerating = false;
        downloadButton.textContent = 'Download PDF';
        downloadButton.removeAttribute('aria-busy');
        updateDownloadButton();
    }
}

async function initialize(): Promise<void> {
    const [heroResult, scenarioResult] = await Promise.allSettled([
        loadHeroChoices(),
        loadScenarioChoices(),
    ]);
    if (heroResult.status === 'fulfilled') {
        renderHeroes(heroResult.value);
    } else {
        console.error(heroResult.reason);
        heroStatus.textContent = 'Could not load hero decks.';
    }
    if (scenarioResult.status === 'fulfilled') {
        renderScenarios(scenarioResult.value);
    } else {
        console.error(scenarioResult.reason);
        scenarioStatus.textContent = 'Could not load scenarios.';
    }
    updateDownloadButton();
}

heroKindButton.addEventListener('click', () => setKind('hero'));
scenarioKindButton.addEventListener('click', () => setKind('scenario'));
downloadButton.addEventListener('click', generatePdf);
setKind('hero');
void initialize();
