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
    finished_at: string;
    hero_name: string;
    villain_name: string;
    expert: number;
    result: 'win'|'loss'|'unknown'|'abandoned';
    rounds: number|null;
    playtime_seconds: number|null;
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
    overview: Overview;
    heroes: RecordRow[];
    villains: RecordRow[];
    matchups: RecordRow[];
    recent_games: RecentGame[];
    achievements: Achievement[];
};

function element<T extends HTMLElement>(id: string): T {
    const found = document.getElementById(id)
    if( !found ) {
        throw new Error(`Missing element: ${id}`)
    }
    return found as T
}

function escapeHtml(value: unknown): string {
    const node = document.createElement('span')
    node.textContent = String(value ?? '')
    return node.innerHTML
}

function displayName(name: string|undefined, code: string|undefined): string {
    return name?.trim() || code?.trim() || 'Unknown'
}

function duration(seconds: number|null|undefined): string {
    if( seconds === null || seconds === undefined || !Number.isFinite(seconds) ) {
        return '—'
    }
    const totalMinutes = Math.max(0, Math.round(seconds / 60))
    const hours = Math.floor(totalMinutes / 60)
    const minutes = totalMinutes % 60
    return hours ? `${hours}h ${minutes}m` : `${minutes}m`
}

function dateTime(value: string): string {
    const date = new Date(value)
    return Number.isNaN(date.valueOf())
        ? value || '—'
        : new Intl.DateTimeFormat(undefined, {dateStyle: 'medium', timeStyle: 'short'}).format(date)
}

function emptyRow(columns: number, text: string): string {
    return `<tr><td class="empty-row" colspan="${columns}">${escapeHtml(text)}</td></tr>`
}

function renderOverview(overview: Overview): void {
    const cards: Array<[string, string]> = [
        [String(overview.completed), 'Completed games'],
        [`${overview.wins}–${overview.losses}`, 'Wins – losses'],
        [`${overview.win_rate.toFixed(1)}%`, 'Win rate'],
        [overview.average_rounds ? overview.average_rounds.toFixed(1) : '—', 'Average rounds'],
        [duration(overview.average_playtime), 'Average time'],
    ]
    element('overview').innerHTML = cards.map(([value, label]) => `
        <article class="overview-card">
            <span class="overview-value">${escapeHtml(value)}</span>
            <span class="overview-label">${escapeHtml(label)}</span>
        </article>
    `).join('')
}

function renderRecords(targetId: string, rows: RecordRow[], type: 'hero'|'villain'): void {
    const target = element<HTMLTableSectionElement>(targetId)
    if( !rows.length ) {
        target.innerHTML = emptyRow(4, 'No completed games yet.')
        return
    }
    target.innerHTML = rows.map(row => {
        const name = type === 'hero'
            ? displayName(row.hero_name, row.hero_code)
            : displayName(row.villain_name, row.villain_code)
        return `<tr>
            <td>${escapeHtml(name)}</td>
            <td>${row.games}</td>
            <td>${row.wins}–${row.losses}</td>
            <td class="rate">${row.win_rate.toFixed(1)}%</td>
        </tr>`
    }).join('')
}

function renderMatchups(rows: RecordRow[]): void {
    const target = element<HTMLTableSectionElement>('matchups')
    if( !rows.length ) {
        target.innerHTML = emptyRow(6, 'No completed matchups yet.')
        return
    }
    target.innerHTML = rows.map(row => `<tr>
        <td>${escapeHtml(displayName(row.hero_name, row.hero_code))}</td>
        <td>${escapeHtml(displayName(row.villain_name, row.villain_code))}</td>
        <td><span class="difficulty ${row.expert ? 'expert' : ''}">${row.expert ? 'Expert' : 'Standard'}</span></td>
        <td>${row.games}</td>
        <td>${row.wins}–${row.losses}</td>
        <td class="rate">${row.win_rate.toFixed(1)}%</td>
    </tr>`).join('')
}

function renderRecent(rows: RecentGame[], unknownGames: number): void {
    const target = element<HTMLTableSectionElement>('recent-games')
    element('unknown-note').textContent = unknownGames
        ? `${unknownGames} imported replay${unknownGames === 1 ? '' : 's'} with unknown result`
        : ''
    if( !rows.length ) {
        target.innerHTML = emptyRow(7, 'No game history yet.')
        return
    }
    target.innerHTML = rows.map(row => `<tr>
        <td>${escapeHtml(dateTime(row.finished_at))}</td>
        <td>${escapeHtml(displayName(row.hero_name, ''))}</td>
        <td>${escapeHtml(displayName(row.villain_name, ''))}</td>
        <td><span class="difficulty ${row.expert ? 'expert' : ''}">${row.expert ? 'Expert' : 'Standard'}</span></td>
        <td><span class="result ${escapeHtml(row.result)}">${escapeHtml(row.result)}</span></td>
        <td>${row.rounds ?? '—'}</td>
        <td>${duration(row.playtime_seconds)}</td>
    </tr>`).join('')
}

function renderAchievements(rows: Achievement[]): void {
    const unlocked = rows.filter(row => row.unlocked).length
    element('achievement-count').textContent = `${unlocked} / ${rows.length} unlocked`
    element('achievements').innerHTML = rows.map(row => {
        const percent = row.target ? Math.min(100, row.progress * 100 / row.target) : 0
        const footer = row.unlocked && row.unlocked_at
            ? `Unlocked ${dateTime(row.unlocked_at)}`
            : `${row.progress} / ${row.target}`
        return `<article class="achievement ${row.unlocked ? 'unlocked' : ''}">
            <h3>${escapeHtml(row.name)}</h3>
            <p>${escapeHtml(row.description)}</p>
            <div class="progress-track" aria-hidden="true"><span style="width:${percent}%"></span></div>
            <div class="achievement-footer"><span>${escapeHtml(footer)}</span><span>${row.unlocked ? 'Unlocked' : 'Locked'}</span></div>
        </article>`
    }).join('')
}

async function loadDashboard(): Promise<void> {
    const loading = element('loading')
    const error = element('error')
    const dashboardElement = element('dashboard')
    try {
        const response = await fetch('/get_game_history')
        const dashboard = await response.json() as Dashboard
        if( !response.ok || !dashboard.available ) {
            throw new Error(dashboard.error || `${response.status} ${response.statusText}`)
        }
        renderOverview(dashboard.overview)
        renderRecords('heroes', dashboard.heroes, 'hero')
        renderRecords('villains', dashboard.villains, 'villain')
        renderMatchups(dashboard.matchups)
        renderRecent(dashboard.recent_games, dashboard.overview.unknown_games)
        renderAchievements(dashboard.achievements)
        loading.hidden = true
        dashboardElement.hidden = false
    } catch( reason ) {
        console.error(reason)
        loading.hidden = true
        error.textContent = reason instanceof Error ? reason.message : 'Could not load game history.'
        error.hidden = false
    }
}

void loadDashboard()
