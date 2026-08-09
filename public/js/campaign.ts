import {
    ActiveCampaignRun,
    CampaignDefinition,
    SavedCampaign,
    campaignDefinitions,
    createInitialCampaignLog,
    getCampaignDefinition,
    getSavedCampaign,
    recordCampaignVictory,
    saveActiveCampaignRun,
    saveCampaign,
} from './campaign_state.js';

type ScenarioData = {
    name: string;
    villain: string[];
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
};

type HeroChoice = {
    id: string;
    name: string;
    imageId: string;
    data: HeroData;
    isUserDeck: boolean;
};

type CampaignChoice = {
    definition: CampaignDefinition;
    imageId: string;
};

type CampaignGamePayload = {
    campaign_json: string;
    encounter_set_names: string[];
    hero_json: string[];
    seed: number;
    timeout: number;
    challenges: string[];
    rules: string[];
    campaign_log: Record<string, string>;
};

const heroStorageKey = 'marvel_lcg_solo_hero';

const savedCampaignSection = document.querySelector<HTMLElement>('#saved-campaign-section')!;
const savedCampaignStatus = document.querySelector<HTMLElement>('#saved-campaign-status')!;
const savedCampaignName = document.querySelector<HTMLElement>('#saved-campaign-name')!;
const savedCampaignSummary = document.querySelector<HTMLElement>('#saved-campaign-summary')!;
const resumeCampaignButton = document.querySelector<HTMLButtonElement>('#resume-campaign-button')!;
const campaignList = document.querySelector<HTMLElement>('#campaign-list')!;
const campaignStatus = document.querySelector<HTMLElement>('#campaign-status')!;
const campaignSelection = document.querySelector<HTMLElement>('#campaign-selection')!;
const scenarioSection = document.querySelector<HTMLElement>('#scenario-section')!;
const scenarioProgress = document.querySelector<HTMLElement>('#scenario-progress')!;
const scenarioPreview = document.querySelector<HTMLElement>('#scenario-preview')!;
const heroList = document.querySelector<HTMLElement>('#hero-list')!;
const heroStatus = document.querySelector<HTMLElement>('#hero-status')!;
const heroSelection = document.querySelector<HTMLElement>('#hero-selection')!;
const playButton = document.querySelector<HTMLButtonElement>('#play-button')!;
const errorMessage = document.querySelector<HTMLElement>('#error-message')!;

const scenarioCache = new Map<string, ScenarioChoice>();
let heroChoices: HeroChoice[] = [];
let selectedCampaign: CampaignDefinition | null = null;
let selectedScenario: ScenarioChoice | null = null;
let selectedHero: HeroChoice | null = null;
let selectedScenarioIndex = 0;
let resumedCampaign: SavedCampaign | null = null;
let isStarting = false;
let selectionRequest = 0;

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

async function loadScenario(scenarioId: string): Promise<ScenarioChoice> {
    const cached = scenarioCache.get(scenarioId);
    if (cached) {
        return cached;
    }

    const data = await fetchJson<ScenarioData>(`/get_scenario_json?${encodeURIComponent(scenarioId)}`);
    const imageId = getFirstCardId(data.villain?.length ? data.villain : data.schemes);
    if (!data.name || !imageId) {
        throw new Error(`Scenario ${scenarioId} has no display data`);
    }

    const choice = { id: scenarioId, name: data.name, imageId, data };
    scenarioCache.set(scenarioId, choice);
    return choice;
}

async function loadCampaignChoices(): Promise<CampaignChoice[]> {
    const choices = await Promise.all(campaignDefinitions.map(async (definition): Promise<CampaignChoice | null> => {
        try {
            const firstScenario = await loadScenario(definition.scenarios[0]);
            return { definition, imageId: firstScenario.imageId };
        } catch (error) {
            console.warn(`Failed to load campaign ${definition.id}`, error);
            return null;
        }
    }));
    return choices.filter((choice): choice is CampaignChoice => choice !== null);
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

function markSelected(container: HTMLElement, selectedId: string): void {
    container.querySelectorAll<HTMLButtonElement>('.choice-card').forEach((button) => {
        const isSelected = button.dataset.id === selectedId;
        button.classList.toggle('selected', isSelected);
        button.setAttribute('aria-pressed', isSelected.toString());
    });
}

function updatePlayButton(): void {
    playButton.disabled = isStarting || !selectedCampaign || !selectedScenario || !selectedHero;
    if (!isStarting) {
        playButton.textContent = resumedCampaign ? 'Continue Campaign' : 'Play';
    }
}

function selectHero(choice: HeroChoice): void {
    selectedHero = choice;
    localStorage.setItem(heroStorageKey, choice.id);
    heroSelection.textContent = choice.name;
    markSelected(heroList, choice.id);
    errorMessage.textContent = '';
    updatePlayButton();
}

function renderScenario(choice: ScenarioChoice, definition: CampaignDefinition): void {
    scenarioSection.hidden = false;
    scenarioProgress.textContent = `Scenario ${selectedScenarioIndex + 1} of ${definition.scenarios.length}`;
    scenarioPreview.replaceChildren();

    const image = document.createElement('img');
    image.src = `/${choice.imageId}`;
    image.alt = '';

    const details = document.createElement('div');
    const title = document.createElement('strong');
    title.textContent = choice.name;
    const text = document.createElement('p');
    text.textContent = 'The scenario is selected automatically from your campaign progress.';
    details.append(title, text);
    scenarioPreview.append(image, details);
}

async function selectCampaign(
    definition: CampaignDefinition,
    saved: SavedCampaign | null,
): Promise<void> {
    const request = ++selectionRequest;
    selectedCampaign = definition;
    resumedCampaign = saved;
    selectedScenario = null;
    selectedScenarioIndex = Math.min(
        Math.max(saved?.scenarioIndex ?? 0, 0),
        definition.scenarios.length - 1,
    );
    campaignSelection.textContent = definition.name;
    markSelected(campaignList, definition.id);
    scenarioSection.hidden = false;
    scenarioPreview.textContent = 'Loading scenario…';
    errorMessage.textContent = '';
    updatePlayButton();

    try {
        const scenario = await loadScenario(definition.scenarios[selectedScenarioIndex]);
        if (request !== selectionRequest) {
            return;
        }
        selectedScenario = scenario;
        renderScenario(scenario, definition);

        if (saved?.heroId) {
            const savedHero = heroChoices.find((choice) => choice.id === saved.heroId);
            if (savedHero) {
                selectHero(savedHero);
            }
        }
    } catch (error) {
        console.error(error);
        if (request === selectionRequest) {
            scenarioPreview.textContent = 'Could not load the current scenario.';
            errorMessage.textContent = 'Could not load this campaign.';
        }
    }
    updatePlayButton();
}

function renderCampaigns(choices: CampaignChoice[]): void {
    campaignList.replaceChildren();
    for (const choice of choices) {
        campaignList.appendChild(createChoiceButton(
            choice.definition.id,
            choice.definition.name,
            choice.imageId,
            () => void selectCampaign(choice.definition, null),
        ));
    }
    campaignStatus.textContent = choices.length ? '' : 'No campaigns are available.';
}

function renderHeroes(choices: HeroChoice[]): void {
    heroChoices = choices;
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

    const savedHeroId = localStorage.getItem(heroStorageKey);
    const savedHero = choices.find((choice) => choice.id === savedHeroId);
    if (savedHero) {
        selectHero(savedHero);
    }
    heroStatus.textContent = choices.length ? '' : 'No starter decks are available.';
}

async function renderSavedCampaign(saved: SavedCampaign | null): Promise<void> {
    if (!saved) {
        savedCampaignSection.hidden = true;
        return;
    }

    const definition = getCampaignDefinition(saved.campaignId);
    if (!definition) {
        savedCampaignSection.hidden = true;
        return;
    }

    const scenarioIndex = Math.min(Math.max(saved.scenarioIndex, 0), definition.scenarios.length - 1);
    const scenario = await loadScenario(definition.scenarios[scenarioIndex]);
    savedCampaignSection.hidden = false;
    savedCampaignName.textContent = definition.name;
    savedCampaignStatus.textContent = saved.completed ? 'Completed' : `Scenario ${scenarioIndex + 1} of ${definition.scenarios.length}`;
    savedCampaignSummary.textContent = saved.completed
        ? `Completed with ${heroChoices.find((choice) => choice.id === saved.heroId)?.name ?? 'your hero'}.`
        : `${scenario.name} · ${heroChoices.find((choice) => choice.id === saved.heroId)?.name ?? 'Starter deck not found'}`;
    resumeCampaignButton.hidden = saved.completed;
    resumeCampaignButton.onclick = () => void selectCampaign(definition, saved);
}

async function initialize(): Promise<void> {
    const [campaignResult, heroResult] = await Promise.allSettled([
        loadCampaignChoices(),
        loadHeroChoices(),
    ]);

    if (campaignResult.status === 'fulfilled') {
        renderCampaigns(campaignResult.value);
    } else {
        console.error(campaignResult.reason);
        campaignStatus.textContent = 'Could not load campaigns.';
    }

    if (heroResult.status === 'fulfilled') {
        renderHeroes(heroResult.value);
    } else {
        console.error(heroResult.reason);
        heroStatus.textContent = 'Could not load starter decks.';
    }

    try {
        await recordCampaignVictory();
        await renderSavedCampaign(getSavedCampaign());
    } catch (error) {
        console.error(error);
        savedCampaignSection.hidden = true;
    }
    updatePlayButton();
}

async function startGame(): Promise<void> {
    if (isStarting || !selectedCampaign || !selectedScenario || !selectedHero) {
        return;
    }

    const existingSave = getSavedCampaign();
    if (
        !resumedCampaign &&
        existingSave &&
        !existingSave.completed &&
        !window.confirm('Starting a new campaign will replace the currently saved campaign. Continue?')
    ) {
        return;
    }

    isStarting = true;
    errorMessage.textContent = '';
    playButton.textContent = 'Creating campaign game…';
    playButton.setAttribute('aria-busy', 'true');
    updatePlayButton();

    const campaignLog = resumedCampaign?.campaignLog ?? createInitialCampaignLog(selectedCampaign.id);
    const scenarioData = {
        ...selectedScenario.data,
        campaign_id: selectedCampaign.id,
    };
    const encounterSetNames = Array.from(new Set([
        ...(selectedScenario.data.encounter_sets ?? []),
        ...(selectedScenario.data.modular_sets ?? []),
    ]));
    const payload: CampaignGamePayload = {
        campaign_json: JSON.stringify(scenarioData),
        encounter_set_names: encounterSetNames,
        hero_json: [JSON.stringify(selectedHero.data)],
        seed: -1,
        timeout: 0,
        challenges: [],
        rules: [
            'mode_campaign',
            'v18_all',
        ],
        campaign_log: campaignLog,
    };

    try {
        const response = await fetch(`/new?data=${encodeURIComponent(JSON.stringify(payload))}`);
        if (!response.ok) {
            throw new Error(`${response.status} ${response.statusText}`);
        }

        const saved: SavedCampaign = {
            version: 1,
            campaignId: selectedCampaign.id,
            scenarioIndex: selectedScenarioIndex,
            heroId: selectedHero.id,
            campaignLog,
            completed: false,
            updatedAt: new Date().toISOString(),
        };
        const activeRun: ActiveCampaignRun = {
            version: 1,
            campaignId: selectedCampaign.id,
            scenarioId: selectedScenario.id,
            scenarioName: selectedScenario.name,
            scenarioIndex: selectedScenarioIndex,
        };
        saveCampaign(saved);
        saveActiveCampaignRun(activeRun);
        window.location.assign('/?p=0');
    } catch (error) {
        console.error(error);
        errorMessage.textContent = 'Could not create the campaign game. Check the server log and try again.';
        isStarting = false;
        playButton.removeAttribute('aria-busy');
        updatePlayButton();
    }
}

playButton.addEventListener('click', startGame);
void initialize();
