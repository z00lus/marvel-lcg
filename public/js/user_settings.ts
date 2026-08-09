export const ANIMATION_TIME_MIN = 0.1
export const ANIMATION_TIME_MAX = 1.5
export const ANIMATION_TIME_DEFAULT = 0.2

const animationTimeKey = 'marvel_lcg_animation_time'
const autoSaveReplaysKey = 'marvel_lcg_autosave_replays'
const marvelCdbDeckIdsKey = 'marvel_lcg_marvelcdb_deck_ids'

function readStorage(key: string): string|null {
    try {
        return localStorage.getItem(key)
    } catch( error ) {
        console.warn(`Could not read browser setting ${key}`, error)
        return null
    }
}

function writeStorage(key: string, value: string) {
    try {
        localStorage.setItem(key, value)
    } catch( error ) {
        console.warn(`Could not save browser setting ${key}`, error)
    }
}

export class UserSettings {
    static getAnimationTime(): number {
        const value = Number(readStorage(animationTimeKey))
        if( Number.isFinite(value) && value >= ANIMATION_TIME_MIN && value <= ANIMATION_TIME_MAX ) {
            return value
        }
        return ANIMATION_TIME_DEFAULT
    }

    static setAnimationTime(value: number) {
        const normalizedValue = Math.min(
            ANIMATION_TIME_MAX,
            Math.max(ANIMATION_TIME_MIN, value),
        )
        writeStorage(animationTimeKey, normalizedValue.toString())
    }

    static getAutoSaveReplays(): boolean {
        return readStorage(autoSaveReplaysKey) === 'true'
    }

    static setAutoSaveReplays(enabled: boolean) {
        writeStorage(autoSaveReplaysKey, enabled.toString())
    }

    static getMarvelCdbDeckIds(): string {
        return readStorage(marvelCdbDeckIdsKey)?.trim() ?? ''
    }

    static setMarvelCdbDeckIds(deckIds: string) {
        writeStorage(marvelCdbDeckIdsKey, deckIds.trim())
    }
}
