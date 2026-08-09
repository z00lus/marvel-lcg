import {
    ANIMATION_TIME_DEFAULT,
    UserSettings,
} from './user_settings.js'

const animationTime = document.getElementById('animation-time') as HTMLInputElement
const animationTimeValue = document.getElementById('animation-time-value') as HTMLOutputElement
const autoSaveReplays = document.getElementById('autosave-replays') as HTMLInputElement
const marvelCdbDeckIds = document.getElementById('marvelcdb-deck-ids') as HTMLInputElement
const marvelCdbSync = document.getElementById('marvelcdb-sync') as HTMLButtonElement
const marvelCdbStatus = document.getElementById('marvelcdb-status') as HTMLElement

type MarvelCdbSyncResult = {
    ok: boolean;
    synced: Array<{id: string; name: string; hero: string}>;
    errors: Array<{id: string; error: string}>;
    synced_at: string;
};

type MarvelCdbSyncStatus = {
    deck_ids: string[];
    last_sync: string;
    last_result: MarvelCdbSyncResult|null;
};

function updateAnimationTime() {
    const value = Number(animationTime.value)
    animationTimeValue.value = `${value.toFixed(1)} s`
    UserSettings.setAnimationTime(value)
}

function parseDeckIds(value: string): string[] {
    const deckIds: string[] = []
    for( const part of value.split(',') ) {
        const deckId = part.trim()
        if( !deckId ) {
            continue
        }
        if( !/^\d+$/.test(deckId) ) {
            throw new Error(`Invalid deck ID: ${deckId}`)
        }
        const normalized = deckId.replace(/^0+(?=\d)/, '')
        if( !deckIds.includes(normalized) ) {
            deckIds.push(normalized)
        }
    }
    return deckIds
}

function updateMarvelCdbControls(showHint=true): string[] {
    const value = marvelCdbDeckIds.value.trim()
    UserSettings.setMarvelCdbDeckIds(value)
    try {
        const deckIds = parseDeckIds(value)
        marvelCdbSync.disabled = deckIds.length === 0
        if( showHint ) {
            marvelCdbStatus.textContent = deckIds.length === 0
                ? 'Enter one or more public MarvelCDB deck IDs.'
                : `${deckIds.length} deck${deckIds.length === 1 ? '' : 's'} ready to sync.`
        }
        return deckIds
    } catch( error ) {
        marvelCdbSync.disabled = true
        marvelCdbStatus.textContent = error instanceof Error ? error.message : String(error)
        return []
    }
}

function formatSyncResult(result: MarvelCdbSyncResult): string {
    const syncedNames = result.synced.map(deck => deck.name)
    const parts: string[] = []
    if( syncedNames.length ) {
        parts.push(`Synced: ${syncedNames.join(', ')}.`)
    }
    if( result.errors.length ) {
        parts.push(result.errors.map(error => `${error.id}: ${error.error}`).join(' '))
    }
    return parts.join(' ') || 'No decks were synchronized.'
}

async function loadMarvelCdbStatus(): Promise<void> {
    try {
        const response = await fetch('/marvelcdb_sync_status')
        if( !response.ok ) {
            throw new Error(`${response.status} ${response.statusText}`)
        }
        const status = await response.json() as MarvelCdbSyncStatus
        if( status.deck_ids.length ) {
            marvelCdbDeckIds.value = status.deck_ids.join(',')
            UserSettings.setMarvelCdbDeckIds(marvelCdbDeckIds.value)
        }
        updateMarvelCdbControls(false)
        marvelCdbStatus.textContent = status.last_result
            ? formatSyncResult(status.last_result)
            : 'Decks have not been synchronized yet.'
    } catch( error ) {
        console.error(error)
        updateMarvelCdbControls(false)
        marvelCdbStatus.textContent = 'Could not load MarvelCDB synchronization status.'
    }
}

animationTime.value = UserSettings.getAnimationTime().toString()
animationTimeValue.value = `${ANIMATION_TIME_DEFAULT.toFixed(1)} s`
updateAnimationTime()

autoSaveReplays.checked = UserSettings.getAutoSaveReplays()
marvelCdbDeckIds.value = UserSettings.getMarvelCdbDeckIds()
updateMarvelCdbControls()

animationTime.addEventListener('input', updateAnimationTime)
autoSaveReplays.addEventListener('change', () => {
    UserSettings.setAutoSaveReplays(autoSaveReplays.checked)
})
marvelCdbDeckIds.addEventListener('input', () => updateMarvelCdbControls())
marvelCdbSync.addEventListener('click', async () => {
    const deckIds = updateMarvelCdbControls(false)
    if( !deckIds.length ) {
        return
    }

    marvelCdbSync.disabled = true
    marvelCdbSync.setAttribute('aria-busy', 'true')
    marvelCdbStatus.textContent = 'Synchronizing decks from MarvelCDB…'
    try {
        const response = await fetch('/sync_marvelcdb_decks', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({deck_ids: deckIds}),
        })
        const result = await response.json() as MarvelCdbSyncResult & {error?: string}
        if( !response.ok ) {
            throw new Error(result.error || `${response.status} ${response.statusText}`)
        }
        marvelCdbStatus.textContent = formatSyncResult(result)
    } catch( error ) {
        console.error(error)
        marvelCdbStatus.textContent = error instanceof Error
            ? error.message
            : 'MarvelCDB synchronization failed.'
    } finally {
        marvelCdbSync.removeAttribute('aria-busy')
        updateMarvelCdbControls(false)
    }
})

void loadMarvelCdbStatus()
