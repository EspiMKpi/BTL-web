/**
 * Shared content helper utilities.
 * Used by moviesPage, discoverPage, seriesPage, and other Alpine components.
 */

const TMDB_IMG_BASE = 'https://image.tmdb.org/t/p/';
const PLACEHOLDER_POSTER = 'https://placehold.co/300x450/1a1a2e/white?text=No+Image';
const PLACEHOLDER_POSTER_SM = 'https://placehold.co/180x270/1a1a2e/white?text=No+Image';
const PLACEHOLDER_POSTER_XS = 'https://placehold.co/46x69/1a1a2e/white?text=%3F';

/**
 * Build a TMDB poster URL.
 * @param {string|null} path - poster_path from TMDB
 * @param {'w92'|'w154'|'w185'|'w342'|'w500'|'w780'|'original'} [size='w500']
 * @returns {string}
 */
export function posterUrl(path, size = 'w500') {
    if (!path) {
        if (size === 'w92') return PLACEHOLDER_POSTER_XS;
        if (size === 'w342') return PLACEHOLDER_POSTER_SM;
        return PLACEHOLDER_POSTER;
    }
    return `${TMDB_IMG_BASE}${size}${path}`;
}

/**
 * Build a TMDB backdrop URL.
 * @param {string|null} path - backdrop_path from TMDB
 * @param {'w300'|'w780'|'w1280'|'original'} [size='original']
 * @returns {string}
 */
export function backdropUrl(path, size = 'original') {
    if (!path) return '';
    return `${TMDB_IMG_BASE}${size}${path}`;
}

/**
 * Get the display title for a content item.
 * Series use `name`, movies use `title`. Falls back gracefully.
 */
export function getTitle(item, contentType) {
    if (contentType === 'series') return item.name || item.title || 'Untitled';
    return item.title || item.name || 'Untitled';
}

/**
 * Get the 4-digit release year.
 */
export function getYear(item, contentType) {
    const d = contentType === 'series' ? item.first_air_date : item.release_date;
    return d ? d.substring(0, 4) : '';
}

/**
 * Format runtime in minutes to "2h 15m" style.
 * @param {number|null} minutes
 * @returns {string}
 */
export function formatRuntime(minutes) {
    if (!minutes || minutes <= 0) return '';
    const h = Math.floor(minutes / 60);
    const m = minutes % 60;
    if (h === 0) return `${m}m`;
    if (m === 0) return `${h}h`;
    return `${h}h ${m}m`;
}

/**
 * Get series status badge info.
 * @param {string|null} status - e.g. "Returning Series", "Ended", "Canceled"
 * @returns {{ label: string, className: string }}
 */
export function getSeriesStatusBadge(status) {
    if (!status) return { label: '', className: '' };
    const map = {
        'Returning Series': { label: 'Airing', className: 'badge--airing' },
        'Ended':            { label: 'Ended', className: 'badge--ended' },
        'Canceled':         { label: 'Canceled', className: 'badge--canceled' },
        'In Production':    { label: 'Coming', className: 'badge--coming' },
    };
    return map[status] || { label: status, className: 'badge--default' };
}

/**
 * Format season/episode count for series cards.
 * e.g. "S3 · 28 Episodes"
 */
export function formatSeriesMeta(item) {
    const seasons = item.number_of_seasons;
    const episodes = item.number_of_episodes;
    if (!seasons && !episodes) return '';
    const parts = [];
    if (seasons) parts.push(`${seasons} Season${seasons > 1 ? 's' : ''}`);
    if (episodes) parts.push(`${episodes} Episode${episodes > 1 ? 's' : ''}`);
    return parts.join(' · ');
}
