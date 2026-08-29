import {
    ActiveCampaignRun,
    CampaignDefinition,
    SavedCampaign,
    campaignDefinitions,
    createInitialCampaignLog,
    getCampaignDefinition,
    getSavedCampaign,
    recordCampaignVictory,
} from './campaign_state.js';
import {
    DeckSourceController,
    createDeckSourceController,
    refreshCampaignDeck,
    saveCampaignDeck,
} from './marvelcdb_deck.js';
import { withCardImageRevision } from './card_image_url.js';

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
    metadata?: Record<string, string>;
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
    isResolvedMarvelCdb?: boolean;
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
    campaign_progress: {
        campaign: SavedCampaign;
        activeRun: ActiveCampaignRun;
        replace: boolean;
    };
};

const heroStorageKey = 'marvel_lcg_solo_hero';

const marvelCdbUpdate = document.querySelector<HTMLButtonElement>('#marvelcdb-update')!;

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
const campaignHeroCache = new Map<string, HeroChoice>();
let heroChoices: HeroChoice[] = [];
let selectedCampaign: CampaignDefinition | null = null;
let selectedScenario: ScenarioChoice | null = null;
let selectedHero: HeroChoice | null = null;
let selectedScenarioIndex = 0;
let resumedCampaign: SavedCampaign | null = null;
let isStarting = false;
let selectionRequest = 0;
let heroBeforeMarvelCdb: HeroChoice | null = null;

let deckSourceController: DeckSourceController | null = null;

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

async function loadHeroChoice(path: string, isUserDeck: boolean): Promise<HeroChoice | null> {
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
}

async function loadHeroChoices(): Promise<HeroChoice[]> {
    // Frozen campaign decks are deliberately not exposed as ordinary choices.
    // They belong to one saved run and are loaded explicitly when that run is
    // resumed; otherwise a new campaign could accidentally reuse and later
    // refresh another campaign's frozen file.
    const [starterPaths, userPaths] = await Promise.all([
        fetchJson<string[]>('/list_starter_deck?'),
        fetchJson<string[]>('/list_user_deck?'),
    ]);
    const deckPaths = [
        ...userPaths.map(path => ({path, isUserDeck: true})),
        ...starterPaths.map(path => ({path, isUserDeck: false})),
    ];
    const choices = await Promise.all(deckPaths.map(
        ({path, isUserDeck}) => loadHeroChoice(path, isUserDeck)));
    return choices.filter((choice): choice is HeroChoice => choice !== null);
}

async function loadCampaignHeroChoice(heroId: string): Promise<HeroChoice | null> {
    const regularChoice = heroChoices.find((choice) => choice.id === heroId);
    if (regularChoice) {
        return regularChoice;
    }
    const cached = campaignHeroCache.get(heroId);
    if (cached) {
        return cached;
    }
    const choice = await loadHeroChoice(heroId, true);
    if (choice) {
        campaignHeroCache.set(heroId, choice);
    }
    return choice;
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
    image.src = withCardImageRevision(`/${imageId}`);
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
    // A resumed campaign already has its frozen deck on disk, so it does not
    // need a freshly resolved one to start the next scenario.
    const awaitingDeck = deckSourceController?.getSource() === 'marvelcdb'
        && !deckSourceController.getDeck()
        && !resumedCampaign;
    playButton.disabled = isStarting
        || deckSourceController?.isBusy() === true
        || !selectedCampaign
        || !selectedScenario
        || !selectedHero
        || awaitingDeck;
    if (!isStarting) {
        playButton.textContent = resumedCampaign ? 'Continue Campaign' : 'Play';
    }
}

/**
 * Offer a MarvelCDB refresh only for a campaign deck that came from MarvelCDB.
 *
 * A campaign deck is frozen once saved; between scenarios the player may
 * deliberately pull the current version, which is the one point in a run where
 * rebuilding is legal.
 */
function updateRefreshButton(): void {
    const deckId = selectedHero?.data.metadata?.marvelcdb_id;
    const isSavedCampaignDeck = resumedCampaign?.heroId === selectedHero?.id;
    marvelCdbUpdate.hidden = !(isSavedCampaignDeck && deckId);
}

function selectHero(
    choice: HeroChoice,
    keepMarvelCdbDeck = false,
    remember = true,
): void {
    if (!keepMarvelCdbDeck) {
        removeResolvedMarvelCdbChoice();
        heroBeforeMarvelCdb = null;
    }
    selectedHero = choice;
    if (remember && !choice.isResolvedMarvelCdb) {
        localStorage.setItem(heroStorageKey, choice.id);
    }
    heroSelection.textContent = choice.name;
    markSelected(heroList, choice.id);
    errorMessage.textContent = '';
    if (!keepMarvelCdbDeck) {
        deckSourceController?.clear();
    }
    updateRefreshButton();
    updatePlayButton();
}

function removeResolvedMarvelCdbChoice(): void {
    heroChoices = heroChoices.filter((choice) => !choice.isResolvedMarvelCdb);
    heroList.querySelector('.resolved-marvelcdb-deck')?.remove();
}

function selectResolvedMarvelCdbDeck(deck: HeroData): string {
    if (selectedHero && !selectedHero.isResolvedMarvelCdb) {
        heroBeforeMarvelCdb = selectedHero;
    }
    removeResolvedMarvelCdbChoice();

    const metadata = deck.metadata ?? {};
    const marvelCdbId = metadata.marvelcdb_id ?? 'loaded';
    const marvelCdbKind = metadata.marvelcdb_kind ?? 'deck';
    const choice: HeroChoice = {
        id: `marvelcdb-${marvelCdbKind}-${marvelCdbId}`,
        name: deck.deck_name ?? deck.name,
        imageId: getFirstCardId(deck.hero ?? []),
        data: deck,
        isUserDeck: true,
        isResolvedMarvelCdb: true,
    };
    heroChoices.unshift(choice);

    const button = createChoiceButton(
        choice.id,
        choice.name,
        choice.imageId,
        () => selectHero(choice, true),
    );
    button.classList.add('user-deck', 'resolved-marvelcdb-deck');
    heroList.prepend(button);
    selectHero(choice, true);
    button.scrollIntoView({block: 'nearest', behavior: 'smooth'});
    return `Loaded and selected ${choice.name}.`;
}

function leaveMarvelCdbMode(): void {
    if (!selectedHero?.isResolvedMarvelCdb) {
        removeResolvedMarvelCdbChoice();
        heroBeforeMarvelCdb = null;
        return;
    }

    const previous = heroBeforeMarvelCdb;
    removeResolvedMarvelCdbChoice();
    heroBeforeMarvelCdb = null;
    if (previous) {
        selectHero(previous, true, false);
    } else {
        selectedHero = null;
        heroSelection.textContent = 'Not selected';
        markSelected(heroList, '');
        updateRefreshButton();
        updatePlayButton();
    }
}

function renderScenario(choice: ScenarioChoice, definition: CampaignDefinition): void {
    scenarioSection.hidden = false;
    scenarioProgress.textContent = `Scenario ${selectedScenarioIndex + 1} of ${definition.scenarios.length}`;
    scenarioPreview.replaceChildren();

    const image = document.createElement('img');
    image.src = withCardImageRevision(`/${choice.imageId}`);
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
    updateRefreshButton();

    // A resumed run may select a frozen deck that is intentionally absent from
    // the normal grid. When the player switches back to starting a new
    // campaign, restore the last ordinary choice instead of leaking that
    // frozen deck into the new run.
    if (!saved && selectedHero && !heroChoices.some((choice) => choice.id === selectedHero?.id)) {
        const regularHero = heroChoices.find(
            (choice) => choice.id === localStorage.getItem(heroStorageKey));
        if (regularHero) {
            selectHero(regularHero);
        } else {
            selectedHero = null;
            heroSelection.textContent = 'Not selected';
            markSelected(heroList, '');
            updateRefreshButton();
        }
    }
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
            const savedHero = await loadCampaignHeroChoice(saved.heroId);
            if (request !== selectionRequest) {
                return;
            }
            if (savedHero) {
                // Do not persist a run-specific file as the user's ordinary
                // deck choice. It must only be selected by this resume path.
                selectHero(savedHero, false, false);
            } else {
                selectedHero = null;
                heroSelection.textContent = 'Saved campaign deck not found';
                markSelected(heroList, '');
                throw new Error(`Saved campaign deck ${saved.heroId} was not found`);
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
    const savedHero = await loadCampaignHeroChoice(saved.heroId);
    const savedHeroName = savedHero?.name ?? 'Saved deck not found';
    savedCampaignSection.hidden = false;
    savedCampaignName.textContent = definition.name;
    savedCampaignStatus.textContent = saved.completed ? 'Completed' : `Scenario ${scenarioIndex + 1} of ${definition.scenarios.length}`;
    savedCampaignSummary.textContent = saved.completed
        ? `Completed with ${savedHeroName}.`
        : `${scenario.name} · ${savedHeroName}`;
    resumeCampaignButton.hidden = saved.completed;
    resumeCampaignButton.onclick = () => void selectCampaign(definition, saved);
}

async function refreshSelectedCampaignDeck(): Promise<void> {
    const heroId = selectedHero?.id;
    if (!heroId || marvelCdbUpdate.disabled) {
        return;
    }

    marvelCdbUpdate.disabled = true;
    const previousLabel = marvelCdbUpdate.textContent;
    marvelCdbUpdate.textContent = 'Updating…';
    errorMessage.textContent = '';

    try {
        const result = await refreshCampaignDeck(heroId);
        const choice = heroChoices.find((entry) => entry.id === heroId);
        if (choice) {
            choice.data = result.deck as HeroData;
        }
        // Silent success reads the same as a no-op, so say what moved.
        errorMessage.textContent = result.changed === 0
            ? 'Deck is already up to date.'
            : `Updated — ${result.changed} card${result.changed === 1 ? '' : 's'} changed.`;
    } catch (error) {
        errorMessage.textContent = error instanceof Error
            ? error.message
            : 'Could not update that deck from MarvelCDB.';
    } finally {
        marvelCdbUpdate.disabled = false;
        marvelCdbUpdate.textContent = previousLabel;
    }
}

async function initialize(): Promise<void> {
    deckSourceController = createDeckSourceController({
        onChange: updatePlayButton,
        onResolved: selectResolvedMarvelCdbDeck,
        onSourceChanged: (source) => {
            if (source === 'precon') {
                leaveMarvelCdbMode();
            }
        },
    });
    marvelCdbUpdate.addEventListener('click', () => void refreshSelectedCampaignDeck());

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
        await renderSavedCampaign(await getSavedCampaign());
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

    let existingSave: SavedCampaign | null;
    try {
        existingSave = await getSavedCampaign();
    } catch (error) {
        console.error(error);
        errorMessage.textContent = 'Could not read campaign progress from the server.';
        return;
    }
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

    // A MarvelCDB deck becomes a file for the run: campaigns persist their hero
    // as a deck id, and freezing it is what stops the deck drifting between
    // scenarios without the player asking.
    let heroDeck: HeroData = selectedHero.data;
    let heroId = selectedHero.id;
    const resolvedDeck = deckSourceController?.getSource() === 'marvelcdb'
        ? deckSourceController.getDeck()
        : null;
    if (resolvedDeck) {
        try {
            const stored = await saveCampaignDeck(selectedCampaign.id, resolvedDeck);
            heroDeck = stored.deck as HeroData;
            heroId = stored.hero_id;
        } catch (error) {
            console.error(error);
            errorMessage.textContent = error instanceof Error
                ? error.message
                : 'Could not save that deck for the campaign.';
            isStarting = false;
            playButton.removeAttribute('aria-busy');
            updatePlayButton();
            return;
        }
    }

    const campaignLog = resumedCampaign?.campaignLog ?? createInitialCampaignLog(selectedCampaign.id);
    const scenarioData = {
        ...selectedScenario.data,
        campaign_id: selectedCampaign.id,
    };
    const encounterSetNames = Array.from(new Set([
        ...(selectedScenario.data.encounter_sets ?? []),
        ...(selectedScenario.data.modular_sets ?? []),
    ]));
    const saved: SavedCampaign = {
        version: 1,
        campaignId: selectedCampaign.id,
        scenarioIndex: selectedScenarioIndex,
        heroId,
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
    const payload: CampaignGamePayload = {
        campaign_json: JSON.stringify(scenarioData),
        encounter_set_names: encounterSetNames,
        hero_json: [JSON.stringify(heroDeck)],
        seed: -1,
        timeout: 0,
        challenges: [],
        rules: [
            'mode_campaign',
            'v18_all',
        ],
        campaign_log: campaignLog,
        campaign_progress: {
            campaign: saved,
            activeRun,
            replace: resumedCampaign === null,
        },
    };

    try {
        const response = await fetch(`/new?data=${encodeURIComponent(JSON.stringify(payload))}`);
        if (!response.ok) {
            const result = await response.json().catch(() => null) as {error?: string} | null;
            throw new Error(result?.error ?? `${response.status} ${response.statusText}`);
        }
        window.location.assign('/table?p=0');
    } catch (error) {
        console.error(error);
        errorMessage.textContent = error instanceof Error
            ? error.message
            : 'Could not create the campaign game. Check the server log and try again.';
        isStarting = false;
        playButton.removeAttribute('aria-busy');
        updatePlayButton();
    }
}

playButton.addEventListener('click', startGame);
void initialize();
