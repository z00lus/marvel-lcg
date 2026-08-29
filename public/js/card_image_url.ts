const cerebroReversedIdentityBaseIds = new Set([
    '16001', // Groot
    '16029', // Rocket Raccoon
    '32001', // Colossus
    '32030', // Shadowcat
    '33001', // Cyclops
    '34001', // Phoenix
    '35001', // Wolverine
    '36001', // Storm
    '37001', // Gambit
    '38001', // Rogue
]);

export const cerebroSideCacheRevision = 'ronin-side-v1';

export function cardImageIdFromUrl(imageUrl: string): string {
    const withoutFragment = imageUrl.split('#', 1)[0];
    const withoutQuery = withoutFragment.split('?', 1)[0];
    return withoutQuery.slice(withoutQuery.lastIndexOf('/') + 1).toLowerCase();
}

export function withCardImageRevision(imageUrl: string): string {
    const cardId = cardImageIdFromUrl(imageUrl);
    const side = cardId.slice(-1);
    const baseId = cardId.slice(0, -1);
    if (
        (side !== 'a' && side !== 'b')
        || !cerebroReversedIdentityBaseIds.has(baseId)
        || /[?&]image-revision=/.test(imageUrl)
    ) {
        return imageUrl;
    }

    const fragmentIndex = imageUrl.indexOf('#');
    const fragment = fragmentIndex >= 0 ? imageUrl.slice(fragmentIndex) : '';
    const baseUrl = fragmentIndex >= 0 ? imageUrl.slice(0, fragmentIndex) : imageUrl;
    const separator = baseUrl.includes('?') ? '&' : '?';
    return `${baseUrl}${separator}image-revision=${cerebroSideCacheRevision}${fragment}`;
}
