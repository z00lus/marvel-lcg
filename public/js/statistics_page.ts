type SourceFilter = 'all'|'digital'|'physical'|'replay_import';
type TabName = 'collection'|'history'|'achievements';

type Overview = {
    completed: number;
    wins: number;
    losses: number;
    win_rate: number;
    unknown_games: number;
    average_rounds: number;
    average_playtime: number;
};

type RecordRow = {
    hero_code?: string;
    hero_name?: string;
    villain_code?: string;
    villain_name?: string;
    expert?: number;
    games: number;
    wins: number;
    losses: number;
    win_rate: number;
};

type RecentGame = {
    id: number;
    finished_at: string;
    hero_code: string;
    hero_name: string;
    villain_code: string;
    villain_name: string;
    scenario_key: string;
    expert: number;
    result: 'win'|'loss'|'unknown'|'abandoned';
    rounds: number|null;
    playtime_seconds: number|null;
    source: 'digital'|'physical'|'replay_import';
    deck_name: string;
    notes: string;
    remaining_hit_points: number|null;
    minions_in_play: number|null;
    side_schemes_in_play: number|null;
};

type Achievement = {
    id: string;
    name: string;
    description: string;
    progress: number;
    target: number;
    unlocked: boolean;
    unlocked_at: string|null;
};

type Dashboard = {
    available: boolean;
    error?: string;
    source_filter: SourceFilter;
    overview: Overview;
    heroes: RecordRow[];
    villains: RecordRow[];
    matchups: RecordRow[];
    recent_games: RecentGame[];
    achievements: Achievement[];
    owned_products: string[];
};

type SetInfo = {
    name: string;
    heroes?: string[];
    scenarios?: string[];
};

type ProductCategory = 'Core Set'|'Expansion'|'Hero Pack'|'Scenario Pack'|'Other';

type Product = {
    key: string;
    order: number;
    name: string;
    category: ProductCategory;
    heroes: string[];
    scenarios: string[];
};

type HeroData = {
    name: string;
    hero: string[];
};

type ScenarioData = {
    name: string;
    villain: string[];
    schemes: string[];
};

type GameChoice = {
    id: string;
    code: string;
    name: string;
};

function element<T extends HTMLElement>(id: string): T {
    const found = document.getElementById(id);
    if (!found) {
        throw new Error(`Missing element: ${id}`);
    }
    return found as T;
}

function escapeHtml(value: unknown): string {
    const node = document.createElement('span');
    node.textContent = String(value ?? '');
    return node.innerHTML;
}

function displayName(name: string|undefined, code: string|undefined): string {
    return name?.trim() || code?.trim() || 'Unknown';
}

function getFileName(path: string): string {
    return path.replace(/^.*[\\/]/, '').replace(/\.[^/.]+$/, '');
}

function firstCardId(cardIds: string[]|undefined): string {
    return cardIds?.[0]?.split(',')[0]?.trim() ?? '';
}

function humanizeId(value: string): string {
    return value.split('_').filter(Boolean).map(word =>
        word.length <= 3 && /^x?\d+$/.test(word)
            ? word.toUpperCase()
            : word.charAt(0).toUpperCase() + word.slice(1),
    ).join(' ');
}

function duration(seconds: number|null|undefined): string {
    if (seconds === null || seconds === undefined || !Number.isFinite(seconds)) {
        return '—';
    }
    const totalMinutes = Math.max(0, Math.round(seconds / 60));
    const hours = Math.floor(totalMinutes / 60);
    const minutes = totalMinutes % 60;
    return hours ? `${hours}h ${minutes}m` : `${minutes}m`;
}

function dateTime(value: string): string {
    const date = new Date(value);
    return Number.isNaN(date.valueOf())
        ? value || '—'
        : new Intl.DateTimeFormat(undefined, {dateStyle: 'medium', timeStyle: 'short'}).format(date);
}

function localDateTimeValue(value: string|Date): string {
    const date = typeof value === 'string' ? new Date(value) : value;
    const local = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
    return local.toISOString().slice(0, 16);
}

function emptyRow(columns: number, text: string): string {
    return `<tr><td class="empty-row" colspan="${columns}">${escapeHtml(text)}</td></tr>`;
}

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
    const response = await fetch(url, options);
    const body = await response.json() as T & {error?: string};
    if (!response.ok) {
        throw new Error(body.error || `${response.status} ${response.statusText}`);
    }
    return body;
}

async function postJson<T>(url: string, data: unknown): Promise<T> {
    return await fetchJson<T>(url, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data),
    });
}

let currentDashboard: Dashboard|null = null;
let sourceFilter: SourceFilter = 'all';
let activeTab: TabName = 'collection';
let setData: Record<string, SetInfo> = {};
let products: Product[] = [];
let ownedProducts = new Set<string>();
let collectionDirty = false;
let productFilter = 'All';
let heroChoices: GameChoice[] = [];
let scenarioChoices: GameChoice[] = [];
let choicesPromise: Promise<void>|null = null;

function invalidateGameChoices(): void {
    heroChoices = [];
    scenarioChoices = [];
    choicesPromise = null;
}

function renderOverview(overview: Overview): void {
    const cards: Array<[string, string]> = [
        [String(overview.completed), 'Completed games'],
        [`${overview.wins}–${overview.losses}`, 'Wins – losses'],
        [`${overview.win_rate.toFixed(1)}%`, 'Win rate'],
        [overview.average_rounds ? overview.average_rounds.toFixed(1) : '—', 'Average rounds'],
        [duration(overview.average_playtime), 'Average time'],
    ];
    element('overview').innerHTML = cards.map(([value, label]) => `
        <article class="overview-card">
            <span class="overview-value">${escapeHtml(value)}</span>
            <span class="overview-label">${escapeHtml(label)}</span>
        </article>
    `).join('');
}

function renderRecords(targetId: string, rows: RecordRow[], type: 'hero'|'villain'): void {
    const target = element<HTMLTableSectionElement>(targetId);
    if (!rows.length) {
        target.innerHTML = emptyRow(4, 'No completed games in this view.');
        return;
    }
    target.innerHTML = rows.map(row => {
        const name = type === 'hero'
            ? displayName(row.hero_name, row.hero_code)
            : displayName(row.villain_name, row.villain_code);
        return `<tr>
            <td>${escapeHtml(name)}</td>
            <td>${row.games}</td>
            <td>${row.wins}–${row.losses}</td>
            <td class="rate">${row.win_rate.toFixed(1)}%</td>
        </tr>`;
    }).join('');
}

function renderMatchups(rows: RecordRow[]): void {
    const target = element<HTMLTableSectionElement>('matchups');
    if (!rows.length) {
        target.innerHTML = emptyRow(6, 'No completed matchups in this view.');
        return;
    }
    target.innerHTML = rows.map(row => `<tr>
        <td>${escapeHtml(displayName(row.hero_name, row.hero_code))}</td>
        <td>${escapeHtml(displayName(row.villain_name, row.villain_code))}</td>
        <td><span class="difficulty ${row.expert ? 'expert' : ''}">${row.expert ? 'Expert' : 'Standard'}</span></td>
        <td>${row.games}</td>
        <td>${row.wins}–${row.losses}</td>
        <td class="rate">${row.win_rate.toFixed(1)}%</td>
    </tr>`).join('');
}

function sourceLabel(source: RecentGame['source']): string {
    if (source === 'physical') return 'Physical';
    if (source === 'replay_import') return 'Replay';
    return 'Digital';
}

function renderRecent(rows: RecentGame[], unknownGames: number): void {
    const target = element<HTMLTableSectionElement>('recent-games');
    element('unknown-note').textContent = unknownGames
        ? `${unknownGames} imported replay${unknownGames === 1 ? '' : 's'} with unknown result`
        : '';
    if (!rows.length) {
        target.innerHTML = emptyRow(9, 'No game history in this view.');
        return;
    }
    target.innerHTML = rows.map(row => {
        const actions = row.source === 'physical'
            ? `<div class="row-actions">
                <button type="button" data-edit-game="${row.id}" title="Edit physical game">Edit</button>
                <button type="button" data-delete-game="${row.id}" class="danger" title="Delete physical game">Delete</button>
            </div>`
            : '';
        return `<tr>
            <td>${escapeHtml(dateTime(row.finished_at))}</td>
            <td><span class="source ${row.source}">${escapeHtml(sourceLabel(row.source))}</span></td>
            <td>${escapeHtml(displayName(row.hero_name, row.hero_code))}</td>
            <td>${escapeHtml(displayName(row.villain_name, row.villain_code))}</td>
            <td><span class="difficulty ${row.expert ? 'expert' : ''}">${row.expert ? 'Expert' : 'Standard'}</span></td>
            <td><span class="result ${escapeHtml(row.result)}">${escapeHtml(row.result)}</span></td>
            <td>${row.rounds ?? '—'}</td>
            <td>${duration(row.playtime_seconds)}</td>
            <td>${actions}</td>
        </tr>`;
    }).join('');

    target.querySelectorAll<HTMLButtonElement>('[data-edit-game]').forEach(button => {
        button.addEventListener('click', () => {
            const id = Number(button.dataset.editGame);
            const game = rows.find(row => row.id === id);
            if (game) void openPhysicalGame(game);
        });
    });
    target.querySelectorAll<HTMLButtonElement>('[data-delete-game]').forEach(button => {
        button.addEventListener('click', () => void deletePhysicalGame(Number(button.dataset.deleteGame)));
    });
}

function renderAchievements(rows: Achievement[]): void {
    const unlocked = rows.filter(row => row.unlocked).length;
    element('achievement-count').textContent = `${unlocked} / ${rows.length} unlocked`;
    element('achievements').innerHTML = rows.map(row => {
        const percent = row.target ? Math.min(100, row.progress * 100 / row.target) : 0;
        const footer = row.unlocked && row.unlocked_at
            ? `Unlocked ${dateTime(row.unlocked_at)}`
            : `${row.progress} / ${row.target}`;
        return `<article class="achievement ${row.unlocked ? 'unlocked' : ''}">
            <h3>${escapeHtml(row.name)}</h3>
            <p>${escapeHtml(row.description)}</p>
            <div class="progress-track" aria-hidden="true"><span style="width:${percent}%"></span></div>
            <div class="achievement-footer"><span>${escapeHtml(footer)}</span><span>${row.unlocked ? 'Unlocked' : 'Locked'}</span></div>
        </article>`;
    }).join('');
}

function productCategory(order: number, info: SetInfo): ProductCategory {
    const heroes = info.heroes?.length ?? 0;
    const scenarios = info.scenarios?.length ?? 0;
    if (order === 1) return 'Core Set';
    if (heroes && scenarios) return 'Expansion';
    if (heroes) return 'Hero Pack';
    if (scenarios) return 'Scenario Pack';
    return 'Other';
}

function buildProducts(sets: Record<string, SetInfo>): Product[] {
    return Object.entries(sets).flatMap(([label, info]) => {
        const match = label.match(/^(\d+)\.\s*(.+)$/);
        if (!match || !info?.name) return [];
        const order = Number(match[1]);
        return [{
            key: info.name,
            order,
            name: match[2],
            category: productCategory(order, info),
            heroes: info.heroes ?? [],
            scenarios: info.scenarios ?? [],
        }];
    }).sort((left, right) => left.order - right.order);
}

function updateCollectionSummary(): void {
    element('collection-count').textContent = `${ownedProducts.size} / ${products.length} owned`;
    const saveButton = element<HTMLButtonElement>('save-collection');
    saveButton.disabled = !collectionDirty;
    saveButton.textContent = collectionDirty ? 'Save Collection' : 'Collection Saved';
}

function renderProductFilters(): void {
    const categories = ['All', 'Core Set', 'Expansion', 'Hero Pack', 'Scenario Pack', 'Other'];
    const target = element('collection-filters');
    target.innerHTML = categories.map(category => `
        <button type="button" data-category="${escapeHtml(category)}" class="${category === productFilter ? 'active' : ''}">
            ${escapeHtml(category)}
        </button>
    `).join('');
    target.querySelectorAll<HTMLButtonElement>('[data-category]').forEach(button => {
        button.addEventListener('click', () => {
            productFilter = button.dataset.category ?? 'All';
            renderProductFilters();
            renderProducts();
        });
    });
}

function renderProducts(): void {
    const query = element<HTMLInputElement>('collection-search').value.trim().toLowerCase();
    const filtered = products.filter(product => {
        const categoryMatches = productFilter === 'All' || product.category === productFilter;
        const textMatches = !query || product.name.toLowerCase().includes(query);
        return categoryMatches && textMatches;
    });
    const target = element('collection-products');
    if (!filtered.length) {
        target.innerHTML = '<p class="empty-products">No products match this filter.</p>';
        return;
    }
    target.innerHTML = filtered.map(product => {
        const owned = ownedProducts.has(product.key);
        const content: string[] = [];
        if (product.heroes.length) content.push(`${product.heroes.length} hero${product.heroes.length === 1 ? '' : 'es'}`);
        if (product.scenarios.length) content.push(`${product.scenarios.length} scenario${product.scenarios.length === 1 ? '' : 's'}`);
        return `<label class="product-card ${owned ? 'owned' : ''}">
            <input type="checkbox" data-product="${escapeHtml(product.key)}" ${owned ? 'checked' : ''}>
            <span class="product-check" aria-hidden="true">${owned ? '✓' : '+'}</span>
            <span class="product-details">
                <span class="product-type">${escapeHtml(product.category)}</span>
                <strong>${escapeHtml(product.name)}</strong>
                <small>${escapeHtml(content.join(' · ') || 'Additional content')}</small>
            </span>
        </label>`;
    }).join('');
    target.querySelectorAll<HTMLInputElement>('[data-product]').forEach(checkbox => {
        checkbox.addEventListener('change', () => {
            const key = checkbox.dataset.product!;
            if (checkbox.checked) ownedProducts.add(key);
            else ownedProducts.delete(key);
            collectionDirty = true;
            invalidateGameChoices();
            renderProducts();
            updateCollectionSummary();
        });
    });
}

function renderCollection(): void {
    renderProductFilters();
    renderProducts();
    updateCollectionSummary();
}

function renderDashboard(dashboard: Dashboard): void {
    renderOverview(dashboard.overview);
    renderRecords('heroes', dashboard.heroes, 'hero');
    renderRecords('villains', dashboard.villains, 'villain');
    renderMatchups(dashboard.matchups);
    renderRecent(dashboard.recent_games, dashboard.overview.unknown_games);
    renderAchievements(dashboard.achievements);
    if (!collectionDirty) {
        ownedProducts = new Set(dashboard.owned_products);
        renderCollection();
    }
    document.querySelectorAll<HTMLButtonElement>('[data-source]').forEach(button => {
        button.classList.toggle('active', button.dataset.source === sourceFilter);
    });
}

async function loadDashboard(): Promise<void> {
    const dashboard = await fetchJson<Dashboard>(`/get_game_history?source=${encodeURIComponent(sourceFilter)}`);
    if (!dashboard.available) {
        throw new Error(dashboard.error || 'Game history is unavailable.');
    }
    currentDashboard = dashboard;
    renderDashboard(dashboard);
}

function setActiveTab(tab: TabName): void {
    activeTab = tab;
    document.querySelectorAll<HTMLButtonElement>('[data-tab]').forEach(button => {
        const active = button.dataset.tab === tab;
        button.classList.toggle('active', active);
        button.setAttribute('aria-selected', String(active));
    });
    document.querySelectorAll<HTMLElement>('[data-panel]').forEach(panel => {
        panel.hidden = panel.dataset.panel !== tab;
    });
    history.replaceState(null, '', `#${tab}`);
}

function selectOptions(select: HTMLSelectElement, choices: GameChoice[], placeholder: string): void {
    select.replaceChildren(new Option(placeholder, ''));
    for (const choice of choices) {
        const option = new Option(choice.name, choice.id);
        option.dataset.code = choice.code;
        select.add(option);
    }
}

async function loadGameChoices(): Promise<void> {
    const [starterPaths, scenarioPaths] = await Promise.all([
        fetchJson<string[]>('/list_starter_deck?'),
        fetchJson<string[]>('/list_scenarios?'),
    ]);
    const availableHeroes = new Set(starterPaths.map(getFileName));
    const availableScenarios = new Set(scenarioPaths.map(getFileName));
    const ownedContent = products.filter(product => ownedProducts.has(product.key));
    const heroIds = Array.from(new Set(ownedContent.flatMap(product => product.heroes)));
    const scenarioIds = Array.from(new Set(ownedContent.flatMap(product => product.scenarios)));

    const heroes = await Promise.all(heroIds.map(async id => {
        if (!availableHeroes.has(id)) {
            return {id, code: '', name: humanizeId(id)};
        }
        try {
            const data = await fetchJson<HeroData>(`/get_hero_json?${encodeURIComponent(id)}`);
            return data.name ? {id, code: firstCardId(data.hero), name: data.name} : null;
        } catch (error) {
            console.warn(`Could not load hero ${id}`, error);
            return {id, code: '', name: humanizeId(id)};
        }
    }));
    const scenarios = await Promise.all(scenarioIds.map(async id => {
        if (!availableScenarios.has(id)) {
            return {id, code: '', name: humanizeId(id)};
        }
        try {
            const data = await fetchJson<ScenarioData>(`/get_scenario_json?${encodeURIComponent(id)}`);
            const code = firstCardId(data.villain?.length ? data.villain : data.schemes);
            return data.name ? {id, code, name: data.name} : null;
        } catch (error) {
            console.warn(`Could not load scenario ${id}`, error);
            return {id, code: '', name: humanizeId(id)};
        }
    }));
    heroChoices = heroes.filter((choice): choice is GameChoice => choice !== null)
        .sort((a, b) => a.name.localeCompare(b.name));
    scenarioChoices = scenarios.filter((choice): choice is GameChoice => choice !== null)
        .sort((a, b) => a.name.localeCompare(b.name));
    selectOptions(
        element<HTMLSelectElement>('physical-hero'),
        heroChoices,
        heroChoices.length ? 'Choose a hero…' : 'No heroes in your collection',
    );
    selectOptions(
        element<HTMLSelectElement>('physical-scenario'),
        scenarioChoices,
        scenarioChoices.length ? 'Choose a scenario…' : 'No scenarios in your collection',
    );
}

async function ensureGameChoices(): Promise<void> {
    if (!choicesPromise) choicesPromise = loadGameChoices();
    await choicesPromise;
}

function selectExistingChoice(
    select: HTMLSelectElement,
    choices: GameChoice[],
    idOrKey: string,
    code: string,
    name: string,
): void {
    const found = choices.find(choice => choice.id === idOrKey || choice.code === code || choice.name === name);
    if (found) {
        select.value = found.id;
        return;
    }
    const option = new Option(name || code || 'Unknown', idOrKey || `manual_${code}`);
    option.dataset.code = code;
    select.add(option);
    select.value = option.value;
}

async function openPhysicalGame(game?: RecentGame): Promise<void> {
    await ensureGameChoices();
    const dialog = element<HTMLDialogElement>('physical-game-dialog');
    const hero = element<HTMLSelectElement>('physical-hero');
    const scenario = element<HTMLSelectElement>('physical-scenario');
    element('physical-game-error').hidden = true;
    element<HTMLInputElement>('physical-game-id').value = game ? String(game.id) : '';
    element('physical-game-title').textContent = game ? 'Edit Physical Game' : 'Log Physical Game';
    element<HTMLSelectElement>('physical-difficulty').value = game?.expert ? 'expert' : 'standard';
    element<HTMLSelectElement>('physical-result').value = game?.result === 'loss' ? 'loss' : 'win';
    element<HTMLInputElement>('physical-date').value = localDateTimeValue(game?.finished_at ?? new Date());
    element<HTMLInputElement>('physical-rounds').value = game?.rounds ? String(game.rounds) : '';
    element<HTMLInputElement>('physical-duration').value = game?.playtime_seconds !== null && game?.playtime_seconds !== undefined
        ? String(Math.round(game.playtime_seconds / 60)) : '';
    element<HTMLInputElement>('physical-hit-points').value = game?.remaining_hit_points !== null && game?.remaining_hit_points !== undefined
        ? String(game.remaining_hit_points) : '';
    element<HTMLInputElement>('physical-clean-table').checked = game?.minions_in_play === 0 && game?.side_schemes_in_play === 0;
    element<HTMLInputElement>('physical-deck').value = game?.deck_name ?? '';
    element<HTMLTextAreaElement>('physical-notes').value = game?.notes ?? '';
    if (game) {
        selectExistingChoice(hero, heroChoices, '', game.hero_code, game.hero_name);
        selectExistingChoice(scenario, scenarioChoices, game.scenario_key, game.villain_code, game.villain_name);
    } else {
        hero.value = '';
        scenario.value = '';
    }
    dialog.showModal();
}

function selectedChoice(select: HTMLSelectElement, choices: GameChoice[]): GameChoice {
    const selected = select.selectedOptions[0];
    if (!selected || !select.value) throw new Error('Choose both a hero and a scenario.');
    return choices.find(choice => choice.id === select.value) ?? {
        id: select.value,
        code: selected.dataset.code ?? '',
        name: selected.text,
    };
}

async function savePhysicalGame(): Promise<void> {
    const hero = selectedChoice(element<HTMLSelectElement>('physical-hero'), heroChoices);
    const scenario = selectedChoice(element<HTMLSelectElement>('physical-scenario'), scenarioChoices);
    const dateValue = element<HTMLInputElement>('physical-date').value;
    if (!dateValue) throw new Error('Played date is required.');
    const rounds = element<HTMLInputElement>('physical-rounds').value;
    const playtime = element<HTMLInputElement>('physical-duration').value;
    const remainingHitPoints = element<HTMLInputElement>('physical-hit-points').value;
    const id = element<HTMLInputElement>('physical-game-id').value;
    await postJson('/physical_games/save', {
        id: id ? Number(id) : null,
        hero_code: hero.code,
        hero_name: hero.name,
        scenario_key: scenario.id,
        villain_code: scenario.code,
        scenario_name: scenario.name,
        expert: element<HTMLSelectElement>('physical-difficulty').value === 'expert',
        result: element<HTMLSelectElement>('physical-result').value,
        finished_at: new Date(dateValue).toISOString(),
        rounds: rounds ? Number(rounds) : null,
        playtime_minutes: playtime ? Number(playtime) : null,
        remaining_hit_points: remainingHitPoints ? Number(remainingHitPoints) : null,
        clean_table: element<HTMLInputElement>('physical-clean-table').checked,
        deck_name: element<HTMLInputElement>('physical-deck').value,
        notes: element<HTMLTextAreaElement>('physical-notes').value,
    });
}

async function deletePhysicalGame(id: number): Promise<void> {
    if (!window.confirm('Delete this manually logged physical game? Statistics and achievements will be recalculated.')) return;
    try {
        await postJson('/physical_games/delete', {id});
        await loadDashboard();
    } catch (reason) {
        window.alert(reason instanceof Error ? reason.message : 'Could not delete the game.');
    }
}

async function saveCollection(): Promise<void> {
    const button = element<HTMLButtonElement>('save-collection');
    button.disabled = true;
    button.textContent = 'Saving…';
    try {
        const result = await postJson<{owned_products: string[]}>('/collection/save', {
            owned_products: Array.from(ownedProducts),
        });
        ownedProducts = new Set(result.owned_products);
        collectionDirty = false;
        invalidateGameChoices();
        renderCollection();
    } catch (reason) {
        window.alert(reason instanceof Error ? reason.message : 'Could not save the collection.');
        button.disabled = false;
        button.textContent = 'Save Collection';
    }
}

function bindEvents(): void {
    document.querySelectorAll<HTMLButtonElement>('[data-tab]').forEach(button => {
        button.addEventListener('click', () => setActiveTab(button.dataset.tab as TabName));
    });
    document.querySelectorAll<HTMLButtonElement>('[data-source]').forEach(button => {
        button.addEventListener('click', async () => {
            sourceFilter = button.dataset.source as SourceFilter;
            try {
                await loadDashboard();
            } catch (reason) {
                window.alert(reason instanceof Error ? reason.message : 'Could not filter game history.');
            }
        });
    });
    element<HTMLInputElement>('collection-search').addEventListener('input', renderProducts);
    element<HTMLButtonElement>('save-collection').addEventListener('click', () => void saveCollection());
    element<HTMLButtonElement>('log-game').addEventListener('click', () => void openPhysicalGame());
    element<HTMLButtonElement>('close-physical-game').addEventListener('click', () => element<HTMLDialogElement>('physical-game-dialog').close());
    element<HTMLButtonElement>('cancel-physical-game').addEventListener('click', () => element<HTMLDialogElement>('physical-game-dialog').close());
    element<HTMLFormElement>('physical-game-form').addEventListener('submit', event => {
        event.preventDefault();
        const button = element<HTMLButtonElement>('save-physical-game');
        const error = element('physical-game-error');
        button.disabled = true;
        button.textContent = 'Saving…';
        error.hidden = true;
        void savePhysicalGame().then(async () => {
            element<HTMLDialogElement>('physical-game-dialog').close();
            await loadDashboard();
            setActiveTab('history');
        }).catch(reason => {
            error.textContent = reason instanceof Error ? reason.message : 'Could not save the game.';
            error.hidden = false;
        }).finally(() => {
            button.disabled = false;
            button.textContent = 'Save Game';
        });
    });
}

async function initialize(): Promise<void> {
    const loading = element('loading');
    const error = element('error');
    const dashboardElement = element('dashboard');
    try {
        setData = await fetchJson<Record<string, SetInfo>>('/get_sets_json?');
        products = buildProducts(setData);
        await loadDashboard();
        bindEvents();
        const requestedTab = location.hash.slice(1) as TabName;
        setActiveTab(['collection', 'history', 'achievements'].includes(requestedTab) ? requestedTab : 'collection');
        loading.hidden = true;
        dashboardElement.hidden = false;
    } catch (reason) {
        console.error(reason);
        loading.hidden = true;
        error.textContent = reason instanceof Error ? reason.message : 'Could not load the archives.';
        error.hidden = false;
    }
}

void initialize();
