type SetInfo = {
    scenarios: string[];
};

type ScenarioData = {
    name: string;
    villain: string[];
    expert: boolean;
    schemes: string[];
    encounter_sets: string[];
    modular_sets: string[];
};

type HeroData = {
    name: string;
    deck_name?: string;
    hero: string[];
    player_deck: string[];
};

type ScenarioChoice = {
    id: string;
    name: string;
    imageId: string;
    data: ScenarioData;
    expertId: string | null;
};

type HeroChoice = {
    id: string;
    name: string;
    imageId: string;
    data: HeroData;
    isUserDeck: boolean;
};

type SoloGamePayload = {
    campaign_json: string;
    encounter_set_names: string[];
    hero_json: string[];
    seed: number;
    timeout: number;
    challenges: string[];
    rules: string[];
    campaign_log: Record<string, string>;
};

const scenarioStorageKey = 'marvel_lcg_solo_scenario';
const heroStorageKey = 'marvel_lcg_solo_hero';

const scenarioList = document.querySelector<HTMLElement>('#scenario-list')!;
const heroList = document.querySelector<HTMLElement>('#hero-list')!;
const scenarioStatus = document.querySelector<HTMLElement>('#scenario-status')!;
const heroStatus = document.querySelector<HTMLElement>('#hero-status')!;
const scenarioSelection = document.querySelector<HTMLElement>('#scenario-selection')!;
const heroSelection = document.querySelector<HTMLElement>('#hero-selection')!;
const playButton = document.querySelector<HTMLButtonElement>('#play-button')!;
const errorMessage = document.querySelector<HTMLElement>('#error-message')!;
const expertMode = document.querySelector<HTMLInputElement>('#expert-mode')!;
const expertModeDescription = document.querySelector<HTMLElement>('#expert-mode-description')!;
const difficultySelection = document.querySelector<HTMLElement>('#difficulty-selection')!;

let selectedScenario: ScenarioChoice | null = null;
let selectedHero: HeroChoice | null = null;
let isStarting = false;

function getFileName(path: string): string {
    return path.replace(/^.*[\\/]/, '').replace(/\.[^/.]+$/, '');
}

function getFirstCardId(cardIds: string[]): string {
    return cardIds[0]?.split(',')[0] ?? '';
}

async function fetchJson<T>(url: string): Promise<T> {
    const response = await fetch(url);
    if (!response.ok) {
        throw new Error(`${response.status} ${response.statusText}`);
    }
    return await response.json() as T;
}

function updatePlayButton(): void {
    playButton.disabled = isStarting || !selectedScenario || !selectedHero;
}

function markSelected(container: HTMLElement, selectedId: string): void {
    container.querySelectorAll<HTMLButtonElement>('.choice-card').forEach((button) => {
        const isSelected = button.dataset.id === selectedId;
        button.classList.toggle('selected', isSelected);
        button.setAttribute('aria-pressed', isSelected.toString());
    });
}

function selectScenario(choice: ScenarioChoice): void {
    selectedScenario = choice;
    localStorage.setItem(scenarioStorageKey, choice.id);
    scenarioSelection.textContent = choice.name;
    markSelected(scenarioList, choice.id);
    errorMessage.textContent = '';

    const hasExpertMode = choice.expertId !== null;
    expertMode.disabled = !hasExpertMode;
    if (!hasExpertMode) {
        expertMode.checked = false;
    }
    difficultySelection.textContent = expertMode.checked ? 'Expert' : 'Standard';
    expertModeDescription.textContent = hasExpertMode
        ? 'Villain stages II–III with the Expert encounter set.'
        : 'Expert setup is not available for this scenario.';
    updatePlayButton();
}

function selectHero(choice: HeroChoice): void {
    selectedHero = choice;
    localStorage.setItem(heroStorageKey, choice.id);
    heroSelection.textContent = choice.name;
    markSelected(heroList, choice.id);
    errorMessage.textContent = '';
    updatePlayButton();
}

function createChoiceButton(
    id: string,
    name: string,
    imageId: string,
    onSelect: () => void,
): HTMLButtonElement {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'choice-card';
    button.dataset.id = id;
    button.setAttribute('aria-pressed', 'false');

    const image = document.createElement('img');
    image.src = `/${imageId}`;
    image.alt = '';

    const title = document.createElement('span');
    title.className = 'choice-name';
    title.textContent = name;

    button.append(image, title);
    button.addEventListener('click', onSelect);
    return button;
}

async function loadScenarioChoices(): Promise<ScenarioChoice[]> {
    const [sets, availablePaths] = await Promise.all([
        fetchJson<Record<string, SetInfo>>('/get_sets_json?'),
        fetchJson<string[]>('/list_scenarios?'),
    ]);
    const availableIds = new Set(availablePaths.map(getFileName));
    const scenarioIds = Array.from(new Set(
        Object.entries(sets)
            .filter(([setName]) => /^\d+\./.test(setName))
            .flatMap(([, set]) => set.scenarios ?? [])
            .filter((id) => availableIds.has(id)),
    ));

    const choices = await Promise.all(scenarioIds.map(async (id): Promise<ScenarioChoice | null> => {
        try {
            const data = await fetchJson<ScenarioData>(`/get_scenario_json?${encodeURIComponent(id)}`);
            const imageId = getFirstCardId(data.villain?.length ? data.villain : data.schemes);
            if (!data.name || !imageId) {
                return null;
            }
            const expertId = `${id}_expert`;
            return {
                id,
                name: data.name,
                imageId,
                data,
                expertId: availableIds.has(expertId) ? expertId : null,
            };
        } catch (error) {
            console.warn(`Failed to load scenario ${id}`, error);
            return null;
        }
    }));

    return choices.filter((choice): choice is ScenarioChoice => choice !== null);
}

async function loadHeroChoices(): Promise<HeroChoice[]> {
    const [starterPaths, userPaths] = await Promise.all([
        fetchJson<string[]>('/list_starter_deck?'),
        fetchJson<string[]>('/list_user_deck?'),
    ]);
    const deckPaths = [
        ...userPaths.map(path => ({path, isUserDeck: true})),
        ...starterPaths.map(path => ({path, isUserDeck: false})),
    ];

    const choices = await Promise.all(deckPaths.map(async ({path, isUserDeck}): Promise<HeroChoice | null> => {
        const id = getFileName(path);
        try {
            const data = await fetchJson<HeroData>(`/get_hero_json?${encodeURIComponent(id)}`);
            const imageId = getFirstCardId(data.hero ?? []);
            if (!data.name || !imageId) {
                return null;
            }
            return {
                id,
                name: data.deck_name ?? data.name,
                imageId,
                data,
                isUserDeck,
            };
        } catch (error) {
            console.warn(`Failed to load hero deck ${id}`, error);
            return null;
        }
    }));

    return choices.filter((choice): choice is HeroChoice => choice !== null);
}

function renderScenarios(choices: ScenarioChoice[]): void {
    const savedId = localStorage.getItem(scenarioStorageKey);
    scenarioList.replaceChildren();

    for (const choice of choices) {
        scenarioList.appendChild(createChoiceButton(
            choice.id,
            choice.name,
            choice.imageId,
            () => selectScenario(choice),
        ));
    }

    const savedChoice = choices.find((choice) => choice.id === savedId);
    if (savedChoice) {
        selectScenario(savedChoice);
    }
    scenarioStatus.textContent = choices.length ? '' : 'No scenarios are available.';
}

function renderHeroes(choices: HeroChoice[]): void {
    const savedId = localStorage.getItem(heroStorageKey);
    heroList.replaceChildren();

    for (const choice of choices) {
        const button = createChoiceButton(
            choice.id,
            choice.name,
            choice.imageId,
            () => selectHero(choice),
        );
        button.classList.toggle('user-deck', choice.isUserDeck);
        heroList.appendChild(button);
    }

    const savedChoice = choices.find((choice) => choice.id === savedId);
    if (savedChoice) {
        selectHero(savedChoice);
    }
    heroStatus.textContent = choices.length ? '' : 'No starter decks are available.';
}

async function initialize(): Promise<void> {
    const [scenarioResult, heroResult] = await Promise.allSettled([
        loadScenarioChoices(),
        loadHeroChoices(),
    ]);

    if (scenarioResult.status === 'fulfilled') {
        renderScenarios(scenarioResult.value);
    } else {
        console.error(scenarioResult.reason);
        scenarioStatus.textContent = 'Could not load scenarios.';
    }

    if (heroResult.status === 'fulfilled') {
        renderHeroes(heroResult.value);
    } else {
        console.error(heroResult.reason);
        heroStatus.textContent = 'Could not load starter decks.';
    }

    updatePlayButton();
}

async function startGame(): Promise<void> {
    if (isStarting || !selectedScenario || !selectedHero) {
        return;
    }

    const scenarioChoice = selectedScenario;
    const heroChoice = selectedHero;

    isStarting = true;
    errorMessage.textContent = '';
    playButton.textContent = 'Creating game…';
    playButton.setAttribute('aria-busy', 'true');
    updatePlayButton();

    try {
        const scenario = expertMode.checked && scenarioChoice.expertId
            ? await fetchJson<ScenarioData>(
                `/get_scenario_json?${encodeURIComponent(scenarioChoice.expertId)}`,
            )
            : scenarioChoice.data;
        const encounterSetNames = Array.from(new Set([
            ...(scenario.encounter_sets ?? []),
            ...(scenario.modular_sets ?? []),
        ]));

        const payload: SoloGamePayload = {
            campaign_json: JSON.stringify(scenario),
            encounter_set_names: encounterSetNames,
            hero_json: [JSON.stringify(heroChoice.data)],
            seed: -1,
            timeout: 0,
            challenges: [],
            rules: ['v18_all'],
            campaign_log: {},
        };

        const response = await fetch(`/new?data=${encodeURIComponent(JSON.stringify(payload))}`);
        if (!response.ok) {
            throw new Error(`${response.status} ${response.statusText}`);
        }
        window.location.assign('/table?p=0');
    } catch (error) {
        console.error(error);
        errorMessage.textContent = 'Could not create the game. Check the server log and try again.';
        isStarting = false;
        playButton.textContent = 'Play';
        playButton.removeAttribute('aria-busy');
        updatePlayButton();
    }
}

playButton.addEventListener('click', startGame);
expertMode.addEventListener('change', () => {
    difficultySelection.textContent = expertMode.checked ? 'Expert' : 'Standard';
});
void initialize();
