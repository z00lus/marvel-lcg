type SetInfo = {
    scenarios: string[];
};

type ScenarioData = {
    name: string;
    villain: string[];
    expert: boolean;
    schemes: string[];
    set_aside: string[];
    encounters: string[];
    underling_sets?: string[];
    encounter_sets: string[];
    modular_sets: string[];
};

type UnderlingData = {
    name: string;
    villain: string[];
    expert_villain: string[];
    set_aside: string[];
    encounters: string[];
};

type UnderlingChoice = {
    id: string;
    name: string;
    imageId: string;
    data: UnderlingData;
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

import {
    DeckSourceController,
    createDeckSourceController,
    getDeckHeroCode,
} from './marvelcdb_deck.js';

const scenarioStorageKey = 'marvel_lcg_solo_scenario';
const heroStorageKey = 'marvel_lcg_solo_hero';
const underlingStorageKey = 'marvel_lcg_solo_underling';
const newScenarioIds = new Set(['protection_racket', 'the_raft_breakout', 'art_museum_heist', 'the_getaway', 'stop_the_presses']);
const newUnderlingIds = new Set(['bullseye', 'electro', 'purple_man']);
const newHeroIds = new Set(['echo', 'daredevil']);

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
const difficultyStepNumber = document.querySelector<HTMLElement>('#difficulty-step-number')!;
const underlingSection = document.querySelector<HTMLElement>('#underling-section')!;
const underlingList = document.querySelector<HTMLElement>('#underling-list')!;
const underlingSelection = document.querySelector<HTMLElement>('#underling-selection')!;
let selectedScenario: ScenarioChoice | null = null;
let selectedHero: HeroChoice | null = null;
let selectedUnderling: UnderlingChoice | null = null;
let underlingChoices: UnderlingChoice[] = [];
let isStarting = false;
let heroChoices: HeroChoice[] = [];

// The precon is the deck that ships with the hero; a MarvelCDB deck replaces
// only the player deck, so the hero choice stays the source of truth for the
// signature cards, obligations and nemesis set.
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

function updatePlayButton(): void {
    const awaitingDeck = deckSourceController?.getSource() === 'marvelcdb'
        && !deckSourceController.getDeck();
    playButton.disabled = isStarting
        || deckSourceController?.isBusy() === true
        || !selectedScenario
        || !selectedHero
        || ((selectedScenario.data.underling_sets?.length ?? 0) > 0 && !selectedUnderling)
        || awaitingDeck;
}

function markSelected(container: HTMLElement, selectedId: string): void {
    container.querySelectorAll<HTMLButtonElement>('.choice-card').forEach((button) => {
        const isSelected = button.dataset.id === selectedId;
        button.classList.toggle('selected', isSelected);
        button.setAttribute('aria-pressed', isSelected.toString());
    });
}

function selectUnderling(choice: UnderlingChoice): void {
    selectedUnderling = choice;
    localStorage.setItem(underlingStorageKey, choice.id);
    underlingSelection.textContent = choice.name;
    markSelected(underlingList, choice.id);
    errorMessage.textContent = '';
    updatePlayButton();
}

async function loadUnderlings(ids: string[]): Promise<void> {
    const generation = ids.join('|');
    selectedUnderling = null;
    underlingChoices = [];
    underlingList.replaceChildren();
    underlingSelection.textContent = 'Not selected';
    underlingSection.hidden = ids.length === 0;
    difficultyStepNumber.textContent = ids.length ? '4' : '3';
    if (!ids.length) {
        updatePlayButton();
        return;
    }

    const choices = (await Promise.all(ids.map(async (id): Promise<UnderlingChoice | null> => {
        try {
            const data = await fetchJson<UnderlingData>(
                `/get_encounter_set_json?${encodeURIComponent(id)}`,
            );
            const imageId = getFirstCardId(data.villain ?? []);
            if (!data.name || !imageId) {
                return null;
            }
            return {id, name: data.name, imageId, data};
        } catch (error) {
            console.warn(`Failed to load underling ${id}`, error);
            return null;
        }
    }))).filter((choice): choice is UnderlingChoice => choice !== null);

    if (selectedScenario?.data.underling_sets?.join('|') !== generation) {
        return;
    }
    underlingChoices = choices;
    for (const choice of choices) {
        underlingList.appendChild(createChoiceButton(
            choice.id,
            choice.name,
            choice.imageId,
            () => selectUnderling(choice),
            newUnderlingIds.has(choice.id),
        ));
    }
    const savedId = localStorage.getItem(underlingStorageKey);
    const savedChoice = choices.find((choice) => choice.id === savedId) ?? choices[0];
    if (savedChoice) {
        selectUnderling(savedChoice);
    }
    updatePlayButton();
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
    void loadUnderlings(choice.data.underling_sets ?? []);
    updatePlayButton();
}

function selectHero(choice: HeroChoice, keepMarvelCdbDeck = false): void {
    selectedHero = choice;
    localStorage.setItem(heroStorageKey, choice.id);
    heroSelection.textContent = choice.name;
    markSelected(heroList, choice.id);
    errorMessage.textContent = '';
    // Picking a different hero by hand abandons a loaded deck; a deck that
    // switched the hero itself keeps it, having just supplied it.
    if (!keepMarvelCdbDeck) {
        deckSourceController?.clear();
    }
    updatePlayButton();
}

function createChoiceButton(
    id: string,
    name: string,
    imageId: string,
    onSelect: () => void,
    isNew = false,
): HTMLButtonElement {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'choice-card';
    button.dataset.id = id;
    button.setAttribute('aria-pressed', 'false');
    button.classList.toggle('new-content', isNew);

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
            // Scenarios with a selectable underling have a separate villain
            // choice below. Their scenario tile should therefore show the
            // main scheme instead of duplicating the first underling's art.
            const imageSource = (data.underling_sets?.length ?? 0) > 0
                ? data.schemes
                : (data.villain?.length ? data.villain : data.schemes);
            const imageId = getFirstCardId(imageSource);
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
    const orderedChoices = [...choices].sort((left, right) =>
        Number(newScenarioIds.has(right.id)) - Number(newScenarioIds.has(left.id)),
    );

    for (const choice of orderedChoices) {
        scenarioList.appendChild(createChoiceButton(
            choice.id,
            choice.name,
            choice.imageId,
            () => selectScenario(choice),
            newScenarioIds.has(choice.id),
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
    heroChoices = choices;
    heroList.replaceChildren();

    for (const choice of choices) {
        const button = createChoiceButton(
            choice.id,
            choice.name,
            choice.imageId,
            () => selectHero(choice),
            !choice.isUserDeck && newHeroIds.has(choice.id),
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
    deckSourceController = createDeckSourceController({
        onChange: updatePlayButton,
        onResolved: (deck) => {
            // The deck names its own hero, so a mismatch with the current
            // selection is corrected rather than rejected.
            const heroCode = getDeckHeroCode(deck);
            const match = heroChoices.find((choice) =>
                getFirstCardId(choice.data.hero ?? []).toLowerCase() === heroCode);
            if (match && match.id !== selectedHero?.id) {
                selectHero(match, true);
                // The hero grid is long; a switch off-screen would look like
                // nothing happened.
                heroList.querySelector(`[data-id="${CSS.escape(match.id)}"]`)
                    ?.scrollIntoView({block: 'nearest', behavior: 'smooth'});
                return `Switched to ${match.data.name}`;
            }
            return null;
        },
    });

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
    const resolvedDeck = deckSourceController?.getSource() === 'marvelcdb'
        ? deckSourceController.getDeck()
        : null;
    if (deckSourceController?.getSource() === 'marvelcdb' && !resolvedDeck) {
        return;
    }

    const scenarioChoice = selectedScenario;
    const heroChoice = selectedHero;
    // A resolved MarvelCDB deck is a complete hero deck -- the conversion keeps
    // the hero, signature cards, obligations and nemesis set from the precon and
    // replaces only the player deck.
    const heroDeck = resolvedDeck ?? heroChoice.data;

    isStarting = true;
    errorMessage.textContent = '';
    playButton.textContent = 'Creating game…';
    playButton.setAttribute('aria-busy', 'true');
    updatePlayButton();

    try {
        const loadedScenario = expertMode.checked && scenarioChoice.expertId
            ? await fetchJson<ScenarioData>(
                `/get_scenario_json?${encodeURIComponent(scenarioChoice.expertId)}`,
            )
            : scenarioChoice.data;
        const scenario = structuredClone(loadedScenario);
        if ((scenario.underling_sets?.length ?? 0) > 0) {
            if (!selectedUnderling) {
                throw new Error('No underling selected');
            }
            scenario.villain = expertMode.checked
                ? selectedUnderling.data.expert_villain
                : selectedUnderling.data.villain;
            scenario.set_aside = [
                ...(scenario.set_aside ?? []),
                ...(selectedUnderling.data.set_aside ?? []),
            ];
            scenario.encounters = [
                ...(scenario.encounters ?? []),
                ...(selectedUnderling.data.encounters ?? []),
            ];
        }
        const encounterSetNames = Array.from(new Set([
            ...(scenario.encounter_sets ?? []),
            ...(scenario.modular_sets ?? []),
        ]));

        const payload: SoloGamePayload = {
            campaign_json: JSON.stringify(scenario),
            encounter_set_names: encounterSetNames,
            hero_json: [JSON.stringify(heroDeck)],
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
