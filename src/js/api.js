/**
 * VozFlix API Client
 * Centralized fetch wrapper with JWT auth, error handling, and auto-logout on 401.
 */

const BASE = '/api';

function getToken() {
    return localStorage.getItem('token');
}

function headers(extra = {}) {
    const h = { 'Content-Type': 'application/json', ...extra };
    const token = getToken();
    if (token) h['Authorization'] = `Bearer ${token}`;
    return h;
}

async function request(method, path, body = null) {
    const opts = { method, headers: headers() };
    if (body) opts.body = JSON.stringify(body);

    const res = await fetch(`${BASE}${path}`, opts);

    if (res.status === 401) {
        localStorage.removeItem('token');
        if (window.Alpine) {
            window.Alpine.store('auth').token = null;
            window.Alpine.store('auth').user = null;
        }
        throw new Error('Session expired. Please sign in again.');
    }

    if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || data.error || `Request failed (${res.status})`);
    }

    return res.json();
}

// ── Content ──────────────────────────────────────────────────────────────

export async function getHomeRails(limit = 10) {
    return request('GET', `/content/home?limit=${limit}`);
}

export async function getGenres() {
    return request('GET', '/content/genres');
}

export async function browseGenre(genreId, page = 1, limit = 20) {
    return request('GET', `/content/browse/${genreId}?page=${page}&limit=${limit}`);
}

export async function searchContent(query, page = 1, limit = 20) {
    return request('GET', `/content/search?q=${encodeURIComponent(query)}&page=${page}&limit=${limit}`);
}

export async function getMovieDetail(movieId) {
    return request('GET', `/content/movie/${movieId}`);
}

export async function getSeriesDetail(seriesId) {
    return request('GET', `/content/series/${seriesId}`);
}

// ── Watchlist ────────────────────────────────────────────────────────────

export async function getWatchlist(statusFilter = null, contentType = null) {
    let params = [];
    if (statusFilter) params.push(`status_filter=${statusFilter}`);
    if (contentType) params.push(`content_type=${contentType}`);
    const qs = params.length ? `?${params.join('&')}` : '';
    return request('GET', `/watchlist/${qs}`);
}

export async function addToWatchlist(contentType, tmdbId, status = 'plan_to_watch', isBookmarked = true) {
    return request('POST', '/watchlist/', { content_type: contentType, tmdb_id: tmdbId, status, is_bookmarked: isBookmarked });
}

export async function updateWatchlistItem(itemId, updates) {
    return request('PATCH', `/watchlist/${itemId}`, updates);
}

export async function removeFromWatchlist(itemId) {
    return request('DELETE', `/watchlist/${itemId}`);
}

// ── History ──────────────────────────────────────────────────────────────

export async function getContinueWatching(limit = 20) {
    return request('GET', `/history/continue-watching?limit=${limit}`);
}

export async function getWatchHistory(contentType = null, page = 1, limit = 50) {
    let params = [`page=${page}`, `limit=${limit}`];
    if (contentType) params.push(`content_type=${contentType}`);
    return request('GET', `/history/?${params.join('&')}`);
}

export async function updateProgress(contentType, tmdbId, progressSeconds, completed = false, seasonNumber = null, episodeNumber = null) {
    return request('POST', '/history/progress', {
        content_type: contentType,
        tmdb_id: tmdbId,
        progress_seconds: progressSeconds,
        completed,
        season_number: seasonNumber,
        episode_number: episodeNumber,
    });
}

// ── Ratings ──────────────────────────────────────────────────────────────

export async function getRatings(tmdbId, contentType = null) {
    let params = [`tmdb_id=${tmdbId}`];
    if (contentType) params.push(`content_type=${contentType}`);
    return request('GET', `/ratings/?${params.join('&')}`);
}

export async function getMyRatings(contentType = null) {
    const qs = contentType ? `?content_type=${contentType}` : '';
    return request('GET', `/ratings/me${qs}`);
}

export async function createRating(contentType, tmdbId, rating, review = null) {
    return request('POST', '/ratings/', { content_type: contentType, tmdb_id: tmdbId, rating, review });
}

export async function deleteRating(contentType, tmdbId) {
    return request('DELETE', '/ratings/', { content_type: contentType, tmdb_id: tmdbId });
}

// ── Profile ──────────────────────────────────────────────────────────────

export async function getProfile() {
    return request('GET', '/profile/');
}

export async function updateProfile(updates) {
    return request('PATCH', '/profile/', updates);
}

export async function getProfileStats() {
    return request('GET', '/profile/stats');
}

export async function getRecentActivity(limit = 20) {
    return request('GET', `/profile/recent-activity?limit=${limit}`);
}

// ── Helpers ──────────────────────────────────────────────────────────────

export function posterUrl(path, size = 'w500') {
    if (!path) return 'https://via.placeholder.com/500x750?text=No+Poster';
    return `https://image.tmdb.org/t/p/${size}${path}`;
}

export function backdropUrl(path, size = 'w1280') {
    if (!path) return 'https://via.placeholder.com/1280x720?text=No+Image';
    return `https://image.tmdb.org/t/p/${size}${path}`;
}

export function formatRuntime(minutes) {
    if (!minutes) return '';
    const h = Math.floor(minutes / 60);
    const m = minutes % 60;
    return h > 0 ? `${h}h ${m}m` : `${m}m`;
}

export function formatDate(dateStr) {
    if (!dateStr) return '';
    return new Date(dateStr).getFullYear().toString();
}

export function genreString(genres) {
    if (!genres || !genres.length) return '';
    return genres.map(g => g.name).join(', ');
}
