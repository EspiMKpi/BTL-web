/**
 * VozFlix shared actions
 * Common helpers used by search, catalog, detail, and watchlist features.
 */

window.showNotification = function(message) {
    let toast = document.getElementById('toast-container');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'toast-container';
        toast.style.cssText = `
            position: fixed;
            bottom: 30px;
            right: 30px;
            background: var(--accent-gold);
            color: black;
            padding: 12px 24px;
            border-radius: 12px;
            font-weight: 600;
            z-index: 2000;
            transform: translateY(100px);
            transition: transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        `;
        document.body.appendChild(toast);
    }
    toast.innerText = message;
    toast.style.transform = 'translateY(0)';
    setTimeout(() => {
        toast.style.transform = 'translateY(100px)';
    }, 3000);
};

window.updateCardVisibility = function(card) {
    const searchMatch = card.dataset.searchMatch !== 'false';
    const filterMatch = card.dataset.filterMatch !== 'false';
    const listMatch = card.dataset.listMatch !== 'false';
    card.style.display = searchMatch && filterMatch && listMatch ? '' : 'none';
};

function normalizeList(value) {
    return (value || '')
        .toLowerCase()
        .split(',')
        .map(item => item.trim())
        .filter(Boolean);
}

function firstCheckedValues(selector) {
    return Array.from(document.querySelectorAll(selector))
        .map(input => input.value?.toLowerCase()?.trim() || input.parentElement.innerText.toLowerCase().trim())
        .filter(Boolean);
}

function deriveCardYear(card) {
    if (card.dataset.year) return card.dataset.year.toLowerCase();
    const statusText = (card.querySelector('.card-status')?.innerText || '').toLowerCase();
    const yearMatch = statusText.match(/\b(19|20)\d{2}\b/);
    return yearMatch ? yearMatch[0] : '';
}

function deriveCardGenres(card) {
    if (card.dataset.genre) return normalizeList(card.dataset.genre);
    const statusText = (card.querySelector('.card-status')?.innerText || '').toLowerCase();
    return normalizeList(statusText.replace(/[\u00b7]/g, ','));
}

function deriveCardType(card) {
    if (card.dataset.type) return card.dataset.type.toLowerCase();
    const statusText = (card.querySelector('.card-status')?.innerText || '').toLowerCase();
    if (statusText.includes('mini')) return 'mini-series';
    if (statusText.includes('series') || statusText.includes('episode') || statusText.includes('season')) return 'series';
    if (statusText.includes('event')) return 'event';
    return 'movie';
}

const TMDB_IMAGE_BASE_URL = 'https://image.tmdb.org/t/p';
const TMDB_API_KEY = '4be043f7fe06cb3995961656ff751a1c';
const TMDB_API_BASE = 'https://api.themoviedb.org/3';

function backendUrl(endpoint, params = {}) {
    const url = new URL(window.location.origin + endpoint);
    Object.entries(params).forEach(([key, value]) => {
        if (value != null) url.searchParams.set(key, value);
    });
    return url.toString();
}

function buildApiUrl(endpoint, params = {}) {
    if (endpoint.startsWith('/api/')) return backendUrl(endpoint, params);
    return tmdbUrl(endpoint, params);
}

function tmdbUrl(endpoint, params = {}) {
    const url = new URL(TMDB_API_BASE + endpoint);
    url.searchParams.set('api_key', TMDB_API_KEY);
    url.searchParams.set('language', 'en-US');
    Object.entries(params).forEach(([key, value]) => {
        if (value != null) url.searchParams.set(key, value);
    });
    return url.toString();
}

function showLoadingState(container, message) {
    if (!container) return;
    container.innerHTML = '<div class="vf-loading"><div class="vf-spinner"></div><p>' + escapeHtml(message || 'Loading...') + '</p></div>';
}

function showErrorState(container, message, retryFn) {
    if (!container) return;
    const retryId = 'retry-' + Date.now() + '-' + Math.random().toString(36).slice(2, 6);
    container.innerHTML = '<div class="vf-error"><div class="vf-error-icon"><svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg></div><h3>Something went wrong</h3><p>' + escapeHtml(message || 'Failed to load content. Please try again.') + '</p>' + (retryFn ? '<button class="btn btn-primary vf-retry-btn" id="' + retryId + '">Try Again</button>' : '') + '</div>';
    if (retryFn) {
        setTimeout(() => {
            const btn = document.getElementById(retryId);
            if (btn) btn.addEventListener('click', retryFn);
        }, 0);
    }
}

function showPageError(pageId, message, retryFn) {
    const host = document.getElementById('page-host');
    if (!host) return;
    const retryId = 'page-retry-' + Date.now();
    host.innerHTML = '<div class="page-content active"><div class="vf-error-page"><div class="vf-error-icon"><svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg></div><h2>Unable to Load Page</h2><p>' + escapeHtml(message || 'We could not load this page. Check your connection and try again.') + '</p>' + (retryFn ? '<button class="btn btn-primary vf-retry-btn" id="' + retryId + '">Retry</button>' : '') + '</div></div>';
    if (retryFn) {
        setTimeout(() => {
            const btn = document.getElementById(retryId);
            if (btn) btn.addEventListener('click', retryFn);
        }, 0);
    }
}

function showGlobalLoading(message) {
    const overlay = document.getElementById('vf-loading-overlay');
    if (!overlay) return;
    const p = overlay.querySelector('p');
    if (p) p.textContent = message || 'Loading content...';
    overlay.style.display = 'flex';
    overlay.classList.remove('fade-out');
}

function hideGlobalLoading() {
    const overlay = document.getElementById('vf-loading-overlay');
    if (!overlay) return;
    overlay.classList.add('fade-out');
    setTimeout(() => {
        overlay.style.display = 'none';
        overlay.classList.remove('fade-out');
    }, 300);
}

function escapeHtml(value) {
    return String(value || '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function formatRating(value) {
    const numericValue = Number(value);
    return Number.isFinite(numericValue) ? numericValue.toFixed(1) : 'N/A';
}

function truncateText(value, maxLength) {
    const text = String(value || '').trim();
    if (!text) return '';
    if (text.length <= maxLength) return text;
    return `${text.slice(0, Math.max(0, maxLength - 1)).trimEnd()}…`;
}

function buildTmdbImageUrl(path, size = 'w500') {
    if (!path) return '';
    if (/^https?:\/\//i.test(path)) return path;
    return `${TMDB_IMAGE_BASE_URL}/${size}${path}`;
}

async function fetchJson(url) {
    const response = await fetch(url);
    if (!response.ok) {
        throw new Error(`Request failed: ${response.status}`);
    }
    return response.json();
}

function normalizeMovieGenres(movie, genreLookup) {
    if (Array.isArray(movie?.genres) && movie.genres.length > 0) {
        return movie.genres.map(genre => genre?.name).filter(Boolean);
    }

    if (Array.isArray(movie?.genre_ids)) {
        return movie.genre_ids.map(genreId => genreLookup?.get(Number(genreId))).filter(Boolean);
    }

    return [];
}

function normalizeMovieRecord(movie, genreLookup) {
    const releaseDate = movie?.release_date || movie?.first_air_date || '';
    const year = releaseDate ? releaseDate.slice(0, 4) : '';
    const genres = normalizeMovieGenres(movie, genreLookup);
    const title = movie?.title || movie?.name || 'Untitled';
    const posterPath = movie?.poster_path || movie?.backdrop_path || '';
    const backdropPath = movie?.backdrop_path || movie?.poster_path || '';
    const status = [year, genres.slice(0, 2).join(' · ')].filter(Boolean).join(' · ');

    return {
        id: movie?.id,
        title,
        overview: movie?.overview || '',
        year,
        genres,
        genreText: genres.join(', '),
        rating: formatRating(movie?.vote_average),
        posterUrl: buildTmdbImageUrl(posterPath, 'w500'),
        backdropUrl: buildTmdbImageUrl(backdropPath, 'w1280'),
        status: status || truncateText(movie?.overview || 'Now streaming', 52),
    };
}

function normalizeSeriesRecord(series, genreLookup) {
    const releaseDate = series?.first_air_date || series?.release_date || '';
    const year = releaseDate ? releaseDate.slice(0, 4) : '';
    const genres = normalizeMovieGenres(series, genreLookup);
    const title = series?.name || series?.title || 'Untitled';
    const posterPath = series?.poster_path || series?.backdrop_path || '';
    const backdropPath = series?.backdrop_path || series?.poster_path || '';
    const statusParts = [year, genres.slice(0, 2).join(' · ')].filter(Boolean);

    return {
        id: series?.id,
        title,
        overview: series?.overview || '',
        year,
        genres,
        genreText: genres.join(', '),
        rating: formatRating(series?.vote_average),
        posterUrl: buildTmdbImageUrl(posterPath, 'w500'),
        backdropUrl: buildTmdbImageUrl(backdropPath, 'w1280'),
        status: statusParts.join(' · ') || truncateText(series?.overview || 'Now streaming', 52),
    };
}

function movieCardMarkup(movie, options = {}) {
    const showBookmark = options.showBookmark === true;
    const cardType = options.type || 'movie';
    const imageUrl = movie.posterUrl || movie.backdropUrl;
    const imageMarkup = imageUrl
        ? `<img src="${escapeHtml(imageUrl)}" alt="${escapeHtml(movie.title)} poster" loading="lazy">`
        : '';
    const bookmarkMarkup = showBookmark
        ? `<div class="bookmark-btn" aria-label="Bookmark ${escapeHtml(movie.title)}"><div class="icon-wrapper" style="width: 14px; height: 14px;"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="m19 21-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16z"/></svg></div></div>`
        : '';

    return `
        <div class="movie-card" data-content-id="${escapeHtml(movie.id)}" data-content-type="${escapeHtml(cardType)}" data-movie-id="${escapeHtml(movie.id)}" data-year="${escapeHtml(movie.year)}" data-genre="${escapeHtml((movie.genres || []).join(','))}" data-type="${escapeHtml(cardType)}" data-status="${escapeHtml(movie.status)}">
            <div class="poster-container">
                ${imageMarkup}
                <span class="rating-badge">${escapeHtml(movie.rating)}</span>
                ${bookmarkMarkup}
            </div>
            <div class="card-info">
                <span class="card-title">${escapeHtml(movie.title)}</span>
                <span class="card-status">${escapeHtml(movie.status)}</span>
            </div>
        </div>`;
}

function top10Markup(movie, rank) {
    return `
        <article class="nf-top10-item" data-content-id="${escapeHtml(movie.id)}" data-content-type="movie">
            <span class="nf-rank">${rank}</span>
            ${movieCardMarkup(movie)}
        </article>`;
}

function renderMovieCards(container, movies, options = {}) {
    if (!container) return;
    container.innerHTML = movies.map((movie, index) => {
        if (options.top10) {
            return top10Markup(movie, index + 1);
        }

        return movieCardMarkup(movie, { showBookmark: options.showBookmark === true, type: options.type || 'movie' });
    }).join('');
}

function renderGenreFilters(containerId, genreMap) {
    const container = document.getElementById(containerId);
    if (!container || !genreMap) return;
    const genres = Array.from(genreMap.entries()).slice(0, 12);
    container.innerHTML = genres.map(([id, name]) =>
        `<label class="custom-checkbox"><input type="checkbox" value="${escapeHtml(name.toLowerCase())}" data-genre-id="${id}"> ${escapeHtml(name)}</label>`
    ).join('');
}

window.backendUrl = backendUrl;
window.buildApiUrl = buildApiUrl;
window.tmdbUrl = tmdbUrl;
window.fetchJson = fetchJson;
window.escapeHtml = escapeHtml;
window.formatRating = formatRating;
window.truncateText = truncateText;
window.buildTmdbImageUrl = buildTmdbImageUrl;
window.showLoadingState = showLoadingState;
window.showErrorState = showErrorState;
window.showPageError = showPageError;
window.showGlobalLoading = showGlobalLoading;
window.hideGlobalLoading = hideGlobalLoading;
window.normalizeMovieRecord = normalizeMovieRecord;
window.normalizeSeriesRecord = normalizeSeriesRecord;
window.renderMovieCards = renderMovieCards;
window.renderGenreFilters = renderGenreFilters;
