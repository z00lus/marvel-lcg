import {
    ANIMATION_TIME_DEFAULT,
    UserSettings,
} from './user_settings.js'

const animationTime = document.getElementById('animation-time') as HTMLInputElement
const animationTimeValue = document.getElementById('animation-time-value') as HTMLOutputElement
const autoSaveReplays = document.getElementById('autosave-replays') as HTMLInputElement
const marvelCdbDeckIds = document.getElementById('marvelcdb-deck-ids') as HTMLInputElement
const marvelCdbDecklistIds = document.getElementById('marvelcdb-decklist-ids') as HTMLInputElement
const marvelCdbLegacyHint = document.getElementById('marvelcdb-legacy-hint') as HTMLElement
const marvelCdbSync = document.getElementById('marvelcdb-sync') as HTMLButtonElement
const marvelCdbStatus = document.getElementById('marvelcdb-status') as HTMLElement

type DeckKind = 'deck'|'decklist'
let syncing = false
let deckInputsEdited = false

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

function parseDeckRef(value: string): {kind: DeckKind|null; id: string} {
    if( /^\d+$/.test(value) ) {
        return {kind: null, id: value.replace(/^0+(?=\d)/, '')}
    }
    try {
        const url = new URL(/^(?:www\.)?marvelcdb\.com\//i.test(value) ? `https://${value}` : value)
        const match = url.pathname.match(/^\/(?:api\/public\/)?(deck|decklist)(?:\/(?:view|edit))?\/(\d+)(?:\.json)?(?:\/.*)?$/i)
        if( ['http:', 'https:'].includes(url.protocol)
            && ['marvelcdb.com', 'www.marvelcdb.com'].includes(url.hostname)
            && match ) {
            return {
                kind: match[1].toLowerCase() as DeckKind,
                id: match[2].replace(/^0+(?=\d)/, ''),
            }
        }
    } catch( error ) {
        // Report malformed URLs with the same message as other invalid input.
    }
    throw new Error(`Invalid MarvelCDB deck ID or link: ${value}`)
}

function parseDeckRefs(value: string, kind: DeckKind): string[] {
    const deckRefs: string[] = []
    for( const part of value.split(',') ) {
        const value = part.trim()
        if( !value ) {
            continue
        }
        const deck = parseDeckRef(value)
        if( deck.kind && deck.kind !== kind ) {
            const field = deck.kind === 'deck' ? 'Personal decks' : 'Published decks'
            throw new Error(`Move this link to ${field}: ${value}`)
        }
        const reference = `https://marvelcdb.com/${kind}/view/${deck.id}`
        if( !deckRefs.includes(reference) ) {
            deckRefs.push(reference)
        }
    }
    return deckRefs
}

function restoreDeckRefs(references: string[]) {
    const personal: string[] = []
    const published: string[] = []
    let hasLegacyIds = false
    for( const reference of references ) {
        const value = reference.trim()
        if( !value ) {
            continue
        }
        try {
            const deck = parseDeckRef(value)
            const target = deck.kind === 'decklist' ? published : personal
            if( !target.includes(deck.id) ) {
                target.push(deck.id)
            }
            hasLegacyIds ||= deck.kind === null
        } catch( error ) {
            // Keep an invalid saved draft visible so the player can correct it.
            personal.push(value)
        }
    }
    marvelCdbDeckIds.value = personal.join(', ')
    marvelCdbDecklistIds.value = published.join(', ')
    marvelCdbLegacyHint.hidden = !hasLegacyIds
}

function updateMarvelCdbControls(showHint=true): string[] {
    UserSettings.setMarvelCdbDeckIds(marvelCdbDeckIds.value)
    UserSettings.setMarvelCdbDecklistIds(marvelCdbDecklistIds.value)
    try {
        const deckIds = [
            ...parseDeckRefs(marvelCdbDeckIds.value, 'deck'),
            ...parseDeckRefs(marvelCdbDecklistIds.value, 'decklist'),
        ]
        marvelCdbSync.disabled = syncing || deckIds.length === 0
        if( showHint && !syncing ) {
            marvelCdbStatus.textContent = deckIds.length === 0
                ? 'Enter one or more deck IDs or links in either field.'
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
        if( deckInputsEdited ) {
            return
        }
        if( status.deck_ids.length ) {
            restoreDeckRefs(status.deck_ids)
        }
        const deckRefs = updateMarvelCdbControls(false)
        if( !deckRefs.length && (marvelCdbDeckIds.value || marvelCdbDecklistIds.value) ) {
            return
        }
        marvelCdbStatus.textContent = status.last_result
            ? formatSyncResult(status.last_result)
            : 'Decks have not been synchronized yet.'
    } catch( error ) {
        console.error(error)
        if( deckInputsEdited ) {
            return
        }
        updateMarvelCdbControls(false)
        marvelCdbStatus.textContent = 'Could not load MarvelCDB synchronization status.'
    }
}

animationTime.value = UserSettings.getAnimationTime().toString()
animationTimeValue.value = `${ANIMATION_TIME_DEFAULT.toFixed(1)} s`
updateAnimationTime()

autoSaveReplays.checked = UserSettings.getAutoSaveReplays()
marvelCdbDeckIds.value = UserSettings.getMarvelCdbDeckIds()
const savedDecklistIds = UserSettings.getMarvelCdbDecklistIds()
if( savedDecklistIds === null ) {
    restoreDeckRefs(marvelCdbDeckIds.value.split(','))
} else {
    marvelCdbDecklistIds.value = savedDecklistIds
}
updateMarvelCdbControls()

animationTime.addEventListener('input', updateAnimationTime)
autoSaveReplays.addEventListener('change', () => {
    UserSettings.setAutoSaveReplays(autoSaveReplays.checked)
})
for( const input of [marvelCdbDeckIds, marvelCdbDecklistIds] ) {
    input.addEventListener('input', () => {
        deckInputsEdited = true
        updateMarvelCdbControls()
    })
}
marvelCdbSync.addEventListener('click', async () => {
    if( syncing || marvelCdbSync.disabled ) {
        return
    }
    const deckIds = updateMarvelCdbControls(false)
    if( !deckIds.length ) {
        return
    }

    syncing = true
    deckInputsEdited = true
    marvelCdbDeckIds.disabled = true
    marvelCdbDecklistIds.disabled = true
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
        marvelCdbLegacyHint.hidden = true
        marvelCdbStatus.textContent = formatSyncResult(result)
    } catch( error ) {
        console.error(error)
        marvelCdbStatus.textContent = error instanceof Error
            ? error.message
            : 'MarvelCDB synchronization failed.'
    } finally {
        syncing = false
        marvelCdbDeckIds.disabled = false
        marvelCdbDecklistIds.disabled = false
        marvelCdbSync.removeAttribute('aria-busy')
        updateMarvelCdbControls(false)
    }
})

void loadMarvelCdbStatus()
