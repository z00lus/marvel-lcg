export type CampaignDefinition = {
    id: string;
    name: string;
    scenarios: string[];
};

export type SavedCampaign = {
    version: 1;
    campaignId: string;
    scenarioIndex: number;
    heroId: string;
    campaignLog: Record<string, string>;
    completed: boolean;
    updatedAt: string;
};

export type ActiveCampaignRun = {
    version: 1;
    campaignId: string;
    scenarioId: string;
    scenarioName: string;
    scenarioIndex: number;
};

type CampaignProgressResponse = {
    campaign: SavedCampaign | null;
    advanced?: boolean;
    migrated?: boolean;
    reason?: string;
};

export const campaignDefinitions: CampaignDefinition[] = [
    {
        id: 'rise_of_red_skull',
        name: 'The Rise of Red Skull',
        scenarios: ['crossbones', 'absorbing_man', 'taskmaster', 'zola', 'red_skull'],
    },
    {
        id: 'galaxys_most_wanted',
        name: "Galaxy's Most Wanted",
        scenarios: ['brotherhood_of_badoon', 'infiltrate_the_museum', 'escape_the_museum', 'nebula', 'ronan'],
    },
    {
        id: 'mad_titans_shadow',
        name: "The Mad Titan's Shadow",
        scenarios: ['ebony_maw', 'the_tower_defense', 'thanos', 'hela', 'loki'],
    },
    {
        id: 'sinister_motives',
        name: 'Sinister Motives',
        scenarios: ['sandman', 'venom', 'mysterio', 'sinister_six', 'venom_goblin'],
    },
    {
        id: 'mutant_genesis',
        name: 'Mutant Genesis',
        scenarios: ['sabretooth', 'project_wideawake', 'master_mold', 'mansion_attack', 'magneto'],
    },
    {
        id: 'next_evolution',
        name: 'NeXt Evolution',
        scenarios: ['morlock_siege', 'on_the_run', 'juggernaut', 'mister_sinister', 'stryfe'],
    },
    {
        id: 'age_of_apocalypse',
        name: 'Age of Apocalypse',
        scenarios: ['unus', 'four_horsemen', 'apocalypse', 'dark_beast', 'en_sabah_nur'],
    },
    {
        id: 'agents_of_shield',
        name: 'Agents of S.H.I.E.L.D.',
        scenarios: ['black_widow', 'batroc', 'modok', 'thunderbolts', 'baron_zemo'],
    },
];

const savedCampaignStorageKey = 'marvel_lcg_solo_campaign_save';
const activeCampaignRunStorageKey = 'marvel_lcg_solo_campaign_active_run';

function loadStorageValue<T>(key: string): T | null {
    const value = localStorage.getItem(key);
    if (!value) {
        return null;
    }

    try {
        return JSON.parse(value) as T;
    } catch (error) {
        console.warn(`Ignoring invalid campaign data in ${key}`, error);
        localStorage.removeItem(key);
        return null;
    }
}

export function getCampaignDefinition(campaignId: string): CampaignDefinition | null {
    return campaignDefinitions.find((definition) => definition.id === campaignId) ?? null;
}

function getLegacySavedCampaign(): SavedCampaign | null {
    const saved = loadStorageValue<SavedCampaign>(savedCampaignStorageKey);
    if (!saved || saved.version !== 1 || !getCampaignDefinition(saved.campaignId)) {
        return null;
    }
    return saved;
}

function getLegacyActiveCampaignRun(): ActiveCampaignRun | null {
    const active = loadStorageValue<ActiveCampaignRun>(activeCampaignRunStorageKey);
    if (!active || active.version !== 1) {
        return null;
    }
    return active;
}

function validateSavedCampaign(saved: SavedCampaign | null): SavedCampaign | null {
    if (!saved || saved.version !== 1 || !getCampaignDefinition(saved.campaignId)) {
        return null;
    }
    return saved;
}

async function parseResponse(response: Response): Promise<CampaignProgressResponse> {
    const result = await response.json() as CampaignProgressResponse & {error?: string};
    if (!response.ok) {
        throw new Error(result.error ?? `${response.status} ${response.statusText}`);
    }
    return result;
}

/**
 * Read the server-owned save, migrating the old browser save exactly once.
 * A server record always wins, so opening the campaign page on an old device
 * can never overwrite progress already continued from another browser.
 */
export async function getSavedCampaign(): Promise<SavedCampaign | null> {
    const response = await parseResponse(await fetch('/campaign_progress?'));
    const serverCampaign = validateSavedCampaign(response.campaign);
    if (serverCampaign) {
        localStorage.removeItem(savedCampaignStorageKey);
        localStorage.removeItem(activeCampaignRunStorageKey);
        return serverCampaign;
    }

    const legacyCampaign = getLegacySavedCampaign();
    if (!legacyCampaign) {
        return null;
    }

    const migration = await parseResponse(await fetch('/campaign_progress/migrate', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            campaign: legacyCampaign,
            activeRun: getLegacyActiveCampaignRun(),
        }),
    }));
    localStorage.removeItem(savedCampaignStorageKey);
    localStorage.removeItem(activeCampaignRunStorageKey);
    return validateSavedCampaign(migration.campaign);
}

export function createInitialCampaignLog(campaignId: string): Record<string, string> {
    if (campaignId !== 'agents_of_shield') {
        return {};
    }

    const randomValue = new Uint32Array(1);
    crypto.getRandomValues(randomValue);
    return {
        'Evidence Seed': String(randomValue[0] % 1_000_000_000),
    };
}

let progressUpdate: Promise<SavedCampaign | null> | null = null;

async function updateCampaignAfterVictory(): Promise<SavedCampaign | null> {
    // A game started before server-owned persistence may still have its
    // campaign marker only in this browser. Migrate it before asking the
    // server to verify and record the victory.
    await getSavedCampaign();
    const result = await parseResponse(await fetch('/campaign_progress/advance', {
        method: 'POST',
    }));
    return validateSavedCampaign(result.campaign);
}

export function recordCampaignVictory(): Promise<SavedCampaign | null> {
    if (!progressUpdate) {
        progressUpdate = updateCampaignAfterVictory().finally(() => {
            progressUpdate = null;
        });
    }
    return progressUpdate;
}
