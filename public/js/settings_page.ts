import {
    ANIMATION_TIME_DEFAULT,
    UserSettings,
} from './user_settings.js'

const animationTime = document.getElementById('animation-time') as HTMLInputElement
const animationTimeValue = document.getElementById('animation-time-value') as HTMLOutputElement
const autoSaveReplays = document.getElementById('autosave-replays') as HTMLInputElement
const marvelCdbUsername = document.getElementById('marvelcdb-username') as HTMLInputElement
const marvelCdbSync = document.getElementById('marvelcdb-sync') as HTMLButtonElement
const marvelCdbStatus = document.getElementById('marvelcdb-status') as HTMLElement

function updateAnimationTime() {
    const value = Number(animationTime.value)
    animationTimeValue.value = `${value.toFixed(1)} s`
    UserSettings.setAnimationTime(value)
}

function updateMarvelCdbControls() {
    const username = marvelCdbUsername.value.trim()
    UserSettings.setMarvelCdbUsername(username)
    marvelCdbSync.disabled = username.length === 0
    marvelCdbStatus.textContent = username.length === 0
        ? 'Enter a username to prepare MarvelCDB synchronization.'
        : 'Username saved locally. Deck synchronization is planned for the next stage.'
}

animationTime.value = UserSettings.getAnimationTime().toString()
animationTimeValue.value = `${ANIMATION_TIME_DEFAULT.toFixed(1)} s`
updateAnimationTime()

autoSaveReplays.checked = UserSettings.getAutoSaveReplays()
marvelCdbUsername.value = UserSettings.getMarvelCdbUsername()
updateMarvelCdbControls()

animationTime.addEventListener('input', updateAnimationTime)
autoSaveReplays.addEventListener('change', () => {
    UserSettings.setAutoSaveReplays(autoSaveReplays.checked)
})
marvelCdbUsername.addEventListener('input', updateMarvelCdbControls)
marvelCdbSync.addEventListener('click', () => {
    updateMarvelCdbControls()
    marvelCdbStatus.textContent = 'MarvelCDB deck synchronization will be added in the next stage.'
})
