/**
 * VozFlix Actions
 * Handles search, filters, and user feedback
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

window.initSearch = function() {
    const searchInputs = document.querySelectorAll('.search-box input, .filter-search input');
    let searchTimeout = null;

    const applySearch = async (rawQuery) => {
        const query = (rawQuery || '').toLowerCase().trim();
        
        if (!query) {
            // Restore default view if query is cleared
            if (document.getElementById('page-movies')?.classList.contains('active') && window._movieCatalogData) {
                renderMoviesCatalog(window._movieCatalogData);
            } else if (document.getElementById('page-series')?.classList.contains('active') && window._seriesCatalogData) {
                renderSeriesCatalog(window._seriesCatalogData);
            } else {
                // For other pages, just fallback to DOM filtering
                document.querySelectorAll('#page-host .movie-card').forEach(card => {
                    card.dataset.searchMatch = 'true';
                    window.updateCardVisibility(card);
                });
            }
            return;
        }

        // Fetch from backend search API
        if (searchTimeout) clearTimeout(searchTimeout);
        searchTimeout = setTimeout(async () => {
            showGlobalLoading('Searching...');
            try {
                const isSeriesPage = document.getElementById('page-series')?.classList.contains('active');
                const isMoviesPage = document.getElementById('page-movies')?.classList.contains('active');
                
                let endpoint = '/api/search';
                if (isSeriesPage) endpoint = '/api/search/series';
                else if (isMoviesPage) endpoint = '/api/search/movies';

                const result = await fetchJson(buildApiUrl(endpoint, { query }));
                const rawResults = result?.results || [];
                const genreLookup = new Map(); // Search results don't strictly need precise genres for standard rendering
                
                if (isSeriesPage) {
                    const items = rawResults.map(r => normalizeSeriesRecord(r, genreLookup));
                    const seriesGrids = document.querySelectorAll('#page-series .movie-grid');
                    if (seriesGrids.length > 0) {
                        seriesGrids[0].innerHTML = '';
                        if (seriesGrids[1]) seriesGrids[1].innerHTML = ''; // Clear second grid
                        renderMovieCards(seriesGrids[0], items, { showBookmark: true, type: 'series' });
                    }
                } else if (isMoviesPage) {
                    const items = rawResults.map(r => normalizeMovieRecord(r, genreLookup));
                    const grid = document.querySelector('#page-movies #search-results-grid');
                    if (grid) {
                        grid.innerHTML = '';
                        renderMovieCards(grid, items, { showBookmark: true });
                    }
                } else {
                    // For discover or home page, try to find a grid
                    const grid = document.querySelector('#page-host .movie-grid');
                    if (grid) {
                        grid.innerHTML = '';
                        const items = rawResults.map(r => r.media_type === 'tv' ? normalizeSeriesRecord(r, genreLookup) : normalizeMovieRecord(r, genreLookup));
                        renderMovieCards(grid, items, { showBookmark: true });
                    }
                }
            } catch (e) {
                console.error("Search failed", e);
                showNotification('Search failed');
            } finally {
                hideGlobalLoading();
            }
        }, 600);
    };

    searchInputs.forEach(input => {
        if (input.dataset.searchBound === 'true') return;
        input.dataset.searchBound = 'true';
        input.addEventListener('input', (e) => applySearch(e.target.value));
    });
};

window.initFilters = function() {
    const filterPanel = document.getElementById('filter-panel');
    const filterToggle = document.getElementById('filter-dropdown-toggle');
    const resultGrid = document.getElementById('search-results-grid');

    if (!filterPanel || !resultGrid) return;

    if (filterToggle && filterToggle.dataset.filterToggleBound !== 'true') {
        filterToggle.dataset.filterToggleBound = 'true';
        filterToggle.addEventListener('click', () => {
            filterPanel.classList.toggle('active');
        });
    }

    const applyFilters = () => {
        const activeYears = firstCheckedValues('#filter-panel .filter-group[data-filter-group="year"] input:checked');
        const activeGenres = firstCheckedValues('#filter-panel .filter-group[data-filter-group="genre"] input:checked');
        const activeTypes = firstCheckedValues('#filter-panel .filter-group[data-filter-group="type"] input:checked');

        const cards = resultGrid.querySelectorAll('.movie-card');

        cards.forEach(card => {
            const year = deriveCardYear(card);
            const genres = deriveCardGenres(card);
            const type = deriveCardType(card);

            const yearMatch = activeYears.length === 0 || activeYears.some(selectedYear => {
                if (selectedYear === 'classic') {
                    const asNumber = Number.parseInt(year, 10);
                    return Number.isFinite(asNumber) && asNumber <= 2022;
                }
                return selectedYear === year;
            });

            const genreMatch = activeGenres.length === 0 || activeGenres.some(selectedGenre =>
                genres.some(genre => genre.includes(selectedGenre))
            );

            const typeMatch = activeTypes.length === 0 || activeTypes.some(selectedType => {
                if (selectedType === 'movie') return type === 'movie';
                return type.includes(selectedType);
            });

            card.dataset.filterMatch = yearMatch && genreMatch && typeMatch ? 'true' : 'false';
            window.updateCardVisibility(card);
        });
    };

    const filterCheckboxes = filterPanel.querySelectorAll('input[type="checkbox"]');
    filterCheckboxes.forEach(checkbox => {
        if (checkbox.dataset.filterBound === 'true') return;
        checkbox.dataset.filterBound = 'true';
        checkbox.addEventListener('change', applyFilters);
    });

    applyFilters();
};

const TMDB_IMAGE_BASE_URL = 'https://image.tmdb.org/t/p';
const TMDB_API_KEY = '4be043f7fe06cb3995961656ff751a1c';
const TMDB_API_BASE = 'https://api.themoviedb.org/3';


function backendUrl(endpoint, params = {}) {
    const url = new URL(window.location.origin + endpoint);
    Object.entries(params).forEach(([k, v]) => { if (v != null) url.searchParams.set(k, v); });
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
    Object.entries(params).forEach(([k, v]) => { if (v != null) url.searchParams.set(k, v); });
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
    setTimeout(() => { overlay.style.display = 'none'; overlay.classList.remove('fade-out'); }, 300);
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

function normalizeMovieGenres(movie, genreLookup) {
    if (Array.isArray(movie?.genres) && movie.genres.length > 0) {
        return movie.genres
            .map(genre => genre?.name)
            .filter(Boolean);
    }

    if (Array.isArray(movie?.genre_ids)) {
        return movie.genre_ids
            .map(genreId => genreLookup.get(Number(genreId)))
            .filter(Boolean);
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

function applyDiscoverHero(movie) {
    const hero = document.querySelector('#page-discover .nf-hero');
    const backdrop = document.querySelector('#page-discover .nf-hero-backdrop');
    const kicker = document.querySelector('#page-discover .nf-kicker');
    const title = document.querySelector('#page-discover .nf-title');
    const copy = document.querySelector('#page-discover .nf-copy');

    if (backdrop && movie.backdropUrl) {
        backdrop.src = movie.backdropUrl;
        backdrop.alt = `${movie.title} backdrop`;
    }

    if (kicker) {
        kicker.textContent = movie.year ? `${movie.year} Spotlight` : 'Featured Movie';
    }

    if (title) {
        title.textContent = movie.title;
    }

    if (copy) {
        copy.textContent = truncateText(movie.overview || 'Browse the latest movies and series pulled from TMDB.', 180);
    }

    if (hero && movie.backdropUrl) {
        hero.style.backgroundImage = `linear-gradient(180deg, rgba(16, 12, 5, 0.18) 0%, rgba(16, 12, 5, 0.74) 100%), url("${movie.backdropUrl}")`;
        hero.style.backgroundSize = 'cover';
        hero.style.backgroundPosition = 'center';
        hero.style.backgroundRepeat = 'no-repeat';
    }
}

function applyMoviesHero(movie) {
    const hero = document.querySelector('#page-movies .catalog-hero');
    const title = document.querySelector('#page-movies .catalog-title');
    const copy = document.querySelector('#page-movies .catalog-copy');
    const metrics = document.querySelectorAll('#page-movies .catalog-metric');

    if (hero && movie.backdropUrl) {
        hero.style.backgroundImage = `linear-gradient(125deg, rgba(38, 26, 8, 0.82), rgba(52, 36, 10, 0.70), rgba(27, 18, 6, 0.88)), url("${movie.backdropUrl}")`;
        hero.style.backgroundSize = 'cover';
        hero.style.backgroundPosition = 'center';
        hero.style.backgroundRepeat = 'no-repeat';
    }

    if (title) {
        title.textContent = movie.title;
    }

    if (copy) {
        copy.textContent = truncateText(movie.overview || 'Discover the latest movies from TMDB, ready to browse by search or filter.', 180);
    }

    if (metrics[0]) {
        const value = metrics[0].querySelector('span');
        const label = metrics[0].querySelector('p');
        if (value) value.textContent = movie.rating;
        if (label) label.textContent = 'TMDB score';
    }

    if (metrics[1]) {
        const value = metrics[1].querySelector('span');
        const label = metrics[1].querySelector('p');
        if (value) value.textContent = movie.year || 'Now';
        if (label) label.textContent = 'Release year';
    }

    if (metrics[2]) {
        const value = metrics[2].querySelector('span');
        const label = metrics[2].querySelector('p');
        if (value) value.textContent = movie.id ? `#${movie.id}` : 'Live';
        if (label) label.textContent = 'Featured pick';
    }
}

function applySeriesHero(series) {
    const hero = document.querySelector('#page-series .catalog-hero');
    const title = document.querySelector('#page-series .catalog-title');
    const copy = document.querySelector('#page-series .catalog-copy');
    const metrics = document.querySelectorAll('#page-series .catalog-metric');

    if (hero && series.backdropUrl) {
        hero.style.backgroundImage = `linear-gradient(125deg, rgba(38, 26, 8, 0.82), rgba(52, 36, 10, 0.70), rgba(27, 18, 6, 0.88)), url("${series.backdropUrl}")`;
        hero.style.backgroundSize = 'cover';
        hero.style.backgroundPosition = 'center';
        hero.style.backgroundRepeat = 'no-repeat';
    }

    if (title) {
        title.textContent = series.title;
    }

    if (copy) {
        copy.textContent = truncateText(series.overview || 'Stream live series and mini-series with poster art pulled from TMDB.', 180);
    }

    if (metrics[0]) {
        const value = metrics[0].querySelector('span');
        const label = metrics[0].querySelector('p');
        if (value) value.textContent = series.rating;
        if (label) label.textContent = 'TMDB score';
    }

    if (metrics[1]) {
        const value = metrics[1].querySelector('span');
        const label = metrics[1].querySelector('p');
        if (value) value.textContent = series.year || 'Now';
        if (label) label.textContent = 'First air year';
    }

    if (metrics[2]) {
        const value = metrics[2].querySelector('span');
        const label = metrics[2].querySelector('p');
        if (value) value.textContent = series.id ? `#${series.id}` : 'Live';
        if (label) label.textContent = 'Featured series';
    }
}

async function fetchJson(url) {
    const response = await fetch(url);
    if (!response.ok) {
        throw new Error(`Request failed: ${response.status}`);
    }
    return response.json();
}

async function fetchGenreMap(_unused) {
    const response = await fetchJson(backendUrl('/api/movies/genres'));
    const genres = Array.isArray(response?.genres) ? response.genres : [];
    const genreMap = new Map();

    genres.forEach(genre => {
        if (genre?.id != null && genre?.name) {
            genreMap.set(Number(genre.id), genre.name);
        }
    });

    return genreMap;
}

function createGenreLookupFromResponse(response) {
    const genres = Array.isArray(response?.genres) ? response.genres : [];
    const genreMap = new Map();

    genres.forEach(genre => {
        if (genre?.id != null && genre?.name) {
            genreMap.set(Number(genre.id), genre.name);
        }
    });

    return genreMap;
}

async function fetchSeriesGenreMap(_unused) {
    const response = await fetchJson(backendUrl('/api/series/genres'));
    return createGenreLookupFromResponse(response);
}

async function fetchMultiPageResults(endpoint, pages, extraParams = {}) {
    const requests = [];
    for (let p = 1; p <= pages; p++) {
        requests.push(fetchJson(buildApiUrl(endpoint, { page: p, ...extraParams })));
    }
    const responses = await Promise.all(requests);
    return responses.flatMap(r => Array.isArray(r?.results) ? r.results : []);
}

async function fetchMoviePageCatalog(apiBaseUrl) {
    const pages = 3; // 3 pages × 20 = 60 items max
    const [popular, topRated, nowPlaying, genreMap] = await Promise.all([
        fetchMultiPageResults('/api/movies/popular', pages),
        fetchMultiPageResults('/api/movies/top-rated', pages),
        fetchMultiPageResults('/api/movies/now-playing', pages),
        fetchGenreMap(),
    ]);

    return { popular, topRated, nowPlaying, genreMap };
}


async function fetchMoviesByGenre(genreId, page) {
    const response = await fetchJson(backendUrl('/api/movies/discover', { with_genres: genreId, page: page || 1, sort_by: 'popularity.desc' }));
    return Array.isArray(response?.results) ? response.results : [];
}

async function fetchSeriesByGenre(genreId, page) {
    const response = await fetchJson(backendUrl('/api/series/discover', { with_genres: genreId, page: page || 1, sort_by: 'popularity.desc' }));
    return Array.isArray(response?.results) ? response.results : [];
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

async function fetchSeriesPageCatalog(apiBaseUrl) {
    const pages = 3; // 3 pages × 20 = 60 items max
    const [popular, topRated, genreMap] = await Promise.all([
        fetchMultiPageResults('/api/series/popular', pages),
        fetchMultiPageResults('/api/series/top-rated', pages),
        fetchSeriesGenreMap(),
    ]);

    return { popular, topRated, genreMap };
}

function renderSeriesCatalog(catalog) {
    window._seriesCatalogData = catalog;
    const heroSeries = normalizeSeriesRecord(catalog.popular[0] || catalog.topRated[0], catalog.genreMap);
    const trendingSeries = (catalog.popular.length > 0 ? catalog.popular : catalog.topRated).slice(0, 15).map(series => normalizeSeriesRecord(series, catalog.genreMap));
    const miniSeries = (catalog.topRated.length > 0 ? catalog.topRated : catalog.popular).slice(0, 15).map(series => normalizeSeriesRecord(series, catalog.genreMap));
    const seriesGrids = document.querySelectorAll('#page-series .movie-grid');

    if (heroSeries.id) {
        applySeriesHero(heroSeries);
    }

    const titleEl = document.getElementById('series-catalog-title');
    const copyEl = document.getElementById('series-catalog-copy');
    if (titleEl) titleEl.textContent = heroSeries.title || 'Series';
    if (copyEl) copyEl.textContent = truncateText(heroSeries.overview || 'Browse the full series catalog.', 180);

    const metricRating = document.querySelector('#series-metric-rating span');
    const metricCount = document.querySelector('#series-metric-count span');
    if (metricRating) metricRating.textContent = heroSeries.rating;
    if (metricCount) metricCount.textContent = trendingSeries.length + miniSeries.length;

    const filtersContainer = document.getElementById('series-filters');
    if (filtersContainer && catalog.genreMap) {
        const genres = Array.from(catalog.genreMap.entries()).slice(0, 8);
        filtersContainer.innerHTML = `<button class="filter-chip active">All</button>` + genres.map(([id, name]) =>
            `<button class="filter-chip" data-genre-id="${id}">${escapeHtml(name)}</button>`
        ).join('');
    }

    if (seriesGrids[0]) renderMovieCards(seriesGrids[0], trendingSeries, { showBookmark: true, type: 'series' });
    if (seriesGrids[1]) renderMovieCards(seriesGrids[1], miniSeries, { showBookmark: true, type: 'series' });
}

function renderDiscoverCatalog(movieCatalog, seriesCatalog) {
    const heroMovie = normalizeMovieRecord(movieCatalog.nowPlaying[0] || movieCatalog.popular[0] || movieCatalog.topRated[0], movieCatalog.genreMap);

    // Populate genre discovery chips
    const genreChipsContainer = document.getElementById('discover-genre-chips');
    if (genreChipsContainer && movieCatalog.genreMap) {
        const allGenres = Array.from(movieCatalog.genreMap.entries());
        genreChipsContainer.innerHTML = '<button class="genre-chip active" data-genre-id="all">All</button>' +
            allGenres.map(([id, name]) => '<button class="genre-chip" data-genre-id="' + id + '">' + escapeHtml(name) + '</button>').join('');

        // Store catalog data for genre filtering
        window._discoverState = { movieCatalog, seriesCatalog };
    }
    const top10Movies = movieCatalog.popular.slice(0, 10).map(movie => normalizeMovieRecord(movie, movieCatalog.genreMap));
    const trendingMovies = (movieCatalog.nowPlaying.length > 0 ? movieCatalog.nowPlaying : movieCatalog.popular).slice(0, 15).map(movie => normalizeMovieRecord(movie, movieCatalog.genreMap));
    const originalsSeries = (seriesCatalog?.topRated?.length > 0 ? seriesCatalog.topRated : seriesCatalog?.popular || []).slice(0, 15).map(series => normalizeSeriesRecord(series, seriesCatalog.genreMap));

    if (heroMovie.id) {
        applyDiscoverHero(heroMovie);
    }

    const top10Title = document.getElementById('discover-top10-title');
    const trendingTitle = document.getElementById('discover-trending-title');
    const seriesTitle = document.getElementById('discover-series-title');
    if (top10Title) top10Title.textContent = `Top 10 in Vietnam Today`;
    if (trendingTitle) trendingTitle.textContent = heroMovie.title ? `${heroMovie.title} & Trending` : 'Trending Now';
    if (seriesTitle) seriesTitle.textContent = originalsSeries.length > 0 ? 'Featured Series' : 'Popular Series';

    renderMovieCards(document.querySelector('#page-discover .nf-top10-grid'), top10Movies, { top10: true });
    renderMovieCards(document.querySelector('#page-discover #discover-trending-grid'), trendingMovies);
    renderMovieCards(document.querySelector('#page-discover #discover-series-grid'), originalsSeries, { type: 'series' });
}

function renderMoviesCatalog(catalog) {
    const heroMovie = normalizeMovieRecord(catalog.popular[0] || catalog.topRated[0] || catalog.nowPlaying[0], catalog.genreMap);
    const movieRows = (catalog.popular.length > 0 ? catalog.popular : catalog.topRated).slice(0, 50).map(movie => normalizeMovieRecord(movie, catalog.genreMap));

    if (heroMovie.id) {
        applyMoviesHero(heroMovie);
    }

    const titleEl = document.getElementById('movies-catalog-title');
    const copyEl = document.getElementById('movies-catalog-copy');
    if (titleEl) titleEl.textContent = heroMovie.title || 'Movies';
    if (copyEl) copyEl.textContent = truncateText(heroMovie.overview || 'Browse the full movie catalog.', 180);

    const metricRating = document.querySelector('#movies-metric-rating span');
    const metricCount = document.querySelector('#movies-metric-count span');
    if (metricRating) metricRating.textContent = heroMovie.rating;
    if (metricCount) metricCount.textContent = movieRows.length;

    renderGenreFilters('movies-filter-genres', catalog.genreMap, 'genre');

    // Store full catalog for client-side filtering
    window._moviesCatalogData = catalog;
    window._moviesAllCards = (catalog.popular.length > 0 ? catalog.popular : catalog.topRated).slice(0, 50).map(m => normalizeMovieRecord(m, catalog.genreMap));

    // Add sort dropdown to filter bar if not already present
    const filterBar = document.querySelector('#page-movies .filter-bar');
    if (filterBar && !document.getElementById('movies-sort-select')) {
        const sortHtml = '<select class="sort-select" id="movies-sort-select"><option value="popularity">Popular</option><option value="rating">Top Rated</option><option value="title">A-Z</option><option value="year-desc">Newest</option><option value="year-asc">Oldest</option></select>';
        filterBar.insertAdjacentHTML('beforeend', sortHtml);
    }
    renderMovieCards(document.querySelector('#page-movies #search-results-grid'), movieRows, { showBookmark: true });

    if (window.initSearch) window.initSearch();
    if (window.initFilters) window.initFilters();
}

function renderGenreFilters(containerId, genreMap, group) {
    const container = document.getElementById(containerId);
    if (!container || !genreMap) return;
    const genres = Array.from(genreMap.entries()).slice(0, 12);
    container.innerHTML = genres.map(([id, name]) =>
        `<label class="custom-checkbox"><input type="checkbox" value="${escapeHtml(name.toLowerCase())}" data-genre-id="${id}"> ${escapeHtml(name)}</label>`
    ).join('');
}

window.initCatalogPage = async function(pageId) {
    if (pageId !== 'discover' && pageId !== 'movies') {
        if (pageId !== 'series') {
            return;
        }
    }

    const apiBaseUrl = window.API_BASE_URL || 'http://localhost:8080';
    const renderToken = `${pageId}-${Date.now()}`;
    window.appState = window.appState || {};
    window.appState.catalogRenderToken = renderToken;

    showGlobalLoading('Loading ' + pageId + '...');

    try {
        if (pageId === 'discover') {
            const [movieCatalog, seriesCatalog] = await Promise.all([
                fetchMoviePageCatalog(apiBaseUrl),
                fetchSeriesPageCatalog(apiBaseUrl),
            ]);

            if (window.appState.catalogRenderToken !== renderToken) {
                return;
            }

            renderDiscoverCatalog(movieCatalog, seriesCatalog);
        } else if (pageId === 'movies') {
            const catalog = await fetchMoviePageCatalog(apiBaseUrl);

            if (window.appState.catalogRenderToken !== renderToken) {
                return;
            }

            renderMoviesCatalog(catalog);
        } else if (pageId === 'series') {
            const catalog = await fetchSeriesPageCatalog(apiBaseUrl);

            if (window.appState.catalogRenderToken !== renderToken) {
                return;
            }

            renderSeriesCatalog(catalog);
        }

        if (window.initSearch) window.initSearch();
        if (window.initFilters) window.initFilters();
        hideGlobalLoading();
    } catch (error) {
        hideGlobalLoading();
        console.warn('Live catalog unavailable, keeping fallback content.', error);
        const grids = document.querySelectorAll('#page-host .movie-grid, #page-host .nf-top10-grid');
        grids.forEach(grid => {
            if (grid && grid.innerHTML.trim() === '') {
                showErrorState(grid, 'Could not load content from TMDB. Check your internet connection.', () => {
                    if (window.initCatalogPage) window.initCatalogPage(pageId);
                });
            }
        });
    }
};

function getSelectedContent() {
    return window.appState?.selectedContent || null;
}

function setTextContent(selector, value) {
    const element = document.querySelector(selector);
    if (element && value) {
        element.textContent = value;
    }
}

function formatCastList(cast) {
    return (Array.isArray(cast) ? cast : [])
        .map(member => member?.name)
        .filter(Boolean)
        .slice(0, 5)
        .join(' · ');
}

function renderSeasonTabs(detail, activeSeasonNumber) {
    const seasonTabs = document.querySelector('#page-detail .season-tabs') || document.querySelector('#page-detail .episode-section .season-tabs');
    if (!seasonTabs) {
        return [];
    }

    const seasons = Array.isArray(detail?.seasons)
        ? detail.seasons.filter(season => season && Number(season.season_number) > 0)
        : [];

    if (seasons.length === 0) {
        seasonTabs.innerHTML = '';
        return [];
    }

    seasonTabs.innerHTML = seasons.map((season, index) => {
        const seasonNumber = Number(season.season_number) || index + 1;
        const activeClass = seasonNumber === activeSeasonNumber ? ' active' : '';
        return `<button class="season-tab${activeClass}" data-season-number="${seasonNumber}">Season ${seasonNumber}</button>`;
    }).join('');

    return seasons;
}

function renderEpisodeCards(episodes) {
    const episodeGrid = document.querySelector('#page-detail .episode-grid');
    if (!episodeGrid) {
        return;
    }

    const episodeList = Array.isArray(episodes) ? episodes : [];
    if (episodeList.length === 0) {
        episodeGrid.innerHTML = '<p class="detail-desc">Episode information is not available for this title.</p>';
        return;
    }

    episodeGrid.innerHTML = episodeList.map(episode => {
        const episodeTitle = episode?.name || `Episode ${episode?.episode_number || ''}`;
        const episodeOverview = episode?.overview || 'No episode description available.';
        const episodeImage = buildTmdbImageUrl(episode?.still_path || episode?.poster_path || '', 'w780');
        return `
            <div class="episode-card" data-episode-number="${escapeHtml(episode?.episode_number)}">
                <div class="ep-thumbnail">
                    <img src="${escapeHtml(episodeImage || 'https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?q=80&w=600&auto=format&fit=crop')}" alt="${escapeHtml(episodeTitle)}">
                    <div class="ep-number">${escapeHtml(episode?.episode_number || '')}</div>
                </div>
                <div class="ep-info">
                    <h3>${escapeHtml(episodeTitle)}</h3>
                    <p>${escapeHtml(truncateText(episodeOverview, 180))}</p>
                </div>
            </div>`;
    }).join('');
}

async function loadDetailSeason(apiBaseUrl, contentId, seasonNumber) {
    const response = await fetchJson(tmdbUrl(`/tv/${contentId}/season/${seasonNumber}`));
    window.appState = window.appState || {};
    window.appState.currentSeasonEpisodes = Array.isArray(response?.episodes) ? response.episodes : [];
    renderEpisodeCards(response?.episodes || []);

    const firstEpisode = Array.isArray(response?.episodes) ? response.episodes[0] : null;
    if (firstEpisode) {
        window.appState.playerOverride = {
            title: `${response?.name || 'Season'} · ${firstEpisode.name || `Episode ${firstEpisode.episode_number}`}`,
            description: firstEpisode.overview || response?.overview || 'Live episode details from TMDB.'
        };
        window.appState.selectedEpisode = firstEpisode;
    }

    return response;
}

window.loadSeasonEpisodes = async function(seasonNumber) {
    const selectedContent = getSelectedContent();
    if (!selectedContent || selectedContent.type !== 'series' || !selectedContent.id) {
        return;
    }

    const apiBaseUrl = window.API_BASE_URL || 'http://localhost:8080';
    try {
        await loadDetailSeason(apiBaseUrl, selectedContent.id, seasonNumber);
    } catch (error) {
        console.warn('Unable to load season episodes.', error);
    }
};

window.initDetailPage = async function() {
    showGlobalLoading('Loading details...');
    const selectedContent = getSelectedContent();
    const apiBaseUrl = window.API_BASE_URL || 'http://localhost:8080';

    if (!selectedContent || !selectedContent.id) {
        return;
    }

    const renderToken = `${selectedContent.type || 'movie'}-${selectedContent.id}-${Date.now()}`;
    window.appState = window.appState || {};
    window.appState.detailRenderToken = renderToken;

    try {
        const isSeries = (selectedContent.type || 'movie') === 'series';
        const detailUrl = isSeries ? tmdbUrl(`/tv/${selectedContent.id}`) : tmdbUrl(`/movie/${selectedContent.id}`);
        const creditsUrl = isSeries ? tmdbUrl(`/tv/${selectedContent.id}/credits`) : tmdbUrl(`/movie/${selectedContent.id}/credits`);
        const [detail, credits] = await Promise.all([fetchJson(detailUrl), fetchJson(creditsUrl)]);

        if (window.appState.detailRenderToken !== renderToken) {
            return;
        }

        const title = detail?.title || detail?.name || selectedContent.title || 'Untitled';
        const overview = detail?.overview || selectedContent.overview || 'Live details pulled from TMDB and cached in MySQL.';
        const releaseDate = detail?.release_date || detail?.first_air_date || selectedContent.year || '';
        const year = releaseDate ? String(releaseDate).slice(0, 4) : selectedContent.year || '';
        const genres = Array.isArray(detail?.genres) ? detail.genres.map(genre => genre?.name).filter(Boolean) : [];
        const runtimeText = isSeries
            ? `${detail?.number_of_seasons || 0} seasons`
            : detail?.runtime
                ? `${detail.runtime}m`
                : '';

        const heroPoster = document.querySelector('#page-detail .detail-hero-poster img');
        const heroTitle = document.querySelector('#page-detail .detail-title');
        const heroDesc = document.querySelector('#page-detail .detail-desc');
        const metaRow = document.querySelector('#page-detail .detail-meta-row');
        const heroScrim = document.querySelector('#page-detail .detail-hero');
        const synopsisCard = document.querySelector('#page-detail .detail-info-card .sidebar-label')?.closest('.detail-info-card');
        const infoCards = document.querySelectorAll('#page-detail .detail-info-card');
        const episodeSection = document.querySelector('#page-detail .episode-section');

        if (heroPoster) {
            const posterPath = detail?.poster_path || selectedContent.poster_path || selectedContent.backdrop_path || '';
            const backdropPath = detail?.backdrop_path || selectedContent.backdrop_path || posterPath;
            heroPoster.src = buildTmdbImageUrl(backdropPath || posterPath, 'w1280') || heroPoster.src;
            heroPoster.alt = `${title} key art`;
            if (heroScrim && backdropPath) {
                heroScrim.style.backgroundImage = `linear-gradient(180deg, rgba(16, 12, 5, 0.20) 0%, rgba(16, 12, 5, 0.82) 100%), url("${buildTmdbImageUrl(backdropPath, 'w1280')}")`;
                heroScrim.style.backgroundSize = 'cover';
                heroScrim.style.backgroundPosition = 'center';
            }
        }

        if (heroTitle) {
            heroTitle.textContent = title;
        }

        if (heroDesc) {
            heroDesc.textContent = overview;
        }

        if (metaRow) {
            const rating = formatRating(detail?.vote_average ?? selectedContent.rating);
            metaRow.innerHTML = `
                <span class="rating">★ ${escapeHtml(rating)}</span>
                <span>${escapeHtml(year || 'Live')}</span>
                <span>${escapeHtml(runtimeText || (isSeries ? 'Series' : 'Movie'))}</span>
                <span>${escapeHtml(genres.length > 0 ? genres.slice(0, 4).join(', ') : (selectedContent.genreText || 'Live catalog'))}</span>`;
        }

        if (infoCards[0]) {
            const synopsisCopy = infoCards[0].querySelector('p:last-child');
            if (synopsisCopy) {
                synopsisCopy.textContent = overview;
            }
        }

        if (infoCards[1]) {
            const castCopy = infoCards[1].querySelector('p:last-child');
            if (castCopy) {
                castCopy.textContent = formatCastList(credits?.cast);
            }
        }

        if (infoCards[2]) {
            const audioCopy = infoCards[2].querySelector('p:last-child');
            if (audioCopy) {
                const languages = Array.isArray(detail?.spoken_languages)
                    ? detail.spoken_languages.map(language => language?.english_name || language?.name).filter(Boolean)
                    : [];
                audioCopy.textContent = `${languages.slice(0, 3).join(', ') || 'Original audio'}${isSeries ? ' · Streaming series' : ' · Streaming film'}`;
            }
        }

        window.appState.selectedContentDetail = detail;

        if (isSeries && episodeSection) {
            episodeSection.style.display = '';
            const seasons = renderSeasonTabs(detail, 1);
            const initialSeasonNumber = seasons[0] ? Number(seasons[0].season_number) || 1 : 1;

            if (seasons.length > 0) {
                await loadDetailSeason(apiBaseUrl, selectedContent.id, initialSeasonNumber);
            }
        } else if (episodeSection) {
            episodeSection.style.display = 'none';
        }

        window.appState.playerOverride = {
            title,
            description: overview
        };
    } catch (error) {
        console.warn('Unable to load detail page data.', error);
        const detailHero = document.querySelector('#page-detail .detail-hero');
        if (detailHero) {
            showErrorState(detailHero, 'Failed to load details. The TMDB API may be unavailable.', () => {
                if (window.initDetailPage) window.initDetailPage();
            });
        }
        if (window.appState) {
            window.appState.playerOverride = {
                title: selectedContent.title || 'Live title',
                description: selectedContent.overview || 'Live details are not available right now.'
            };
        }
    }
    hideGlobalLoading();
};

window.initWatchlistsPage = async function() {
    const apiBaseUrl = window.API_BASE_URL || 'http://localhost:8080';
    const userId = window.appState?.userId || 1;

    try {
        const watchlistResponse = await fetchJson(`${apiBaseUrl}/api/watchlist/${userId}`);
        const watchlistItems = Array.isArray(watchlistResponse?.items) ? watchlistResponse.items : [];

        const statusCounts = { continue: 0, wishlist: 0, completed: 0, favorites: 0, all: watchlistItems.length };
        watchlistItems.forEach(item => {
            if (statusCounts[item.status] !== undefined) statusCounts[item.status]++;
        });

        const countAll = document.getElementById('watchlist-count-all');
        const countContinue = document.getElementById('watchlist-count-continue');
        const countWishlist = document.getElementById('watchlist-count-wishlist');
        const countCompleted = document.getElementById('watchlist-count-completed');
        const countFavorites = document.getElementById('watchlist-count-favorites');
        if (countAll) countAll.textContent = statusCounts.all;
        if (countContinue) countContinue.textContent = statusCounts.continue;
        if (countWishlist) countWishlist.textContent = statusCounts.wishlist;
        if (countCompleted) countCompleted.textContent = statusCounts.completed;
        if (countFavorites) countFavorites.textContent = statusCounts.favorites;

        const watchlistGrid = document.querySelector('#page-watchlists .watchlist-grid');
        if (!watchlistGrid || watchlistItems.length === 0) {
            const [movieResponse, seriesResponse] = await Promise.all([
                fetchJson(`${apiBaseUrl}/api/movies/popular?page=1`),
                fetchJson(`${apiBaseUrl}/api/series/popular?page=1`)
            ]);
            const movieGenreMap = new Map();
            const seriesGenreMap = new Map();
            (Array.isArray(movieResponse?.genres) ? movieResponse.genres : []).forEach(genre => movieGenreMap.set(Number(genre.id), genre.name));
            (Array.isArray(seriesResponse?.genres) ? seriesResponse.genres : []).forEach(genre => seriesGenreMap.set(Number(genre.id), genre.name));
            const movieItems = (Array.isArray(movieResponse?.results) ? movieResponse.results : []).slice(0, 3).map(movie => normalizeMovieRecord(movie, movieGenreMap));
            const seriesItems = (Array.isArray(seriesResponse?.results) ? seriesResponse.results : []).slice(0, 2).map(series => normalizeSeriesRecord(series, seriesGenreMap));
            const mergedItems = [...movieItems, ...seriesItems].slice(0, 6);
            const statuses = ['continue', 'wishlist', 'favorites', 'completed', 'continue', 'wishlist'];

            if (watchlistGrid) {
                watchlistGrid.innerHTML = mergedItems.map((item, index) => {
                    const status = statuses[index] || 'wishlist';
                    return `
                        <div class="movie-card" data-status="${status}" data-content-id="${escapeHtml(item.id)}" data-content-type="${index >= movieItems.length ? 'series' : 'movie'}">
                            <div class="poster-container">
                                <img src="${escapeHtml(item.posterUrl || item.backdropUrl)}" alt="${escapeHtml(item.title)}" loading="lazy">
                                <span class="rating-badge">${escapeHtml(item.rating)}</span>
                                <div class="bookmark-btn"><div class="icon-wrapper" style="width: 14px; height: 14px;"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="m19 21-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16z"/></svg></div></div>
                            </div>
                            <div class="card-info"><span class="card-title">${escapeHtml(item.title)}</span><span class="card-status">${escapeHtml(status)}</span></div>
                        </div>`;
                }).join('');
            }
            return;
        }

        const tmdbIds = watchlistItems.map(item => ({ id: item.tmdbId, type: item.contentType, status: item.status }));
        const movieIds = tmdbIds.filter(i => i.type === 'movie').map(i => i.id);
        const seriesIds = tmdbIds.filter(i => i.type === 'series').map(i => i.id);

        const statusMap = {};
        tmdbIds.forEach(i => statusMap[`${i.type}-${i.id}`] = i.status);

        const allItems = [];
        for (const id of movieIds) {
            try {
                const detail = await fetchJson(tmdbUrl(`/movie/${id}`));
                const record = normalizeMovieRecord(detail, new Map());
                const status = statusMap[`movie-${id}`] || 'wishlist';
                allItems.push({ ...record, status, _type: 'movie' });
            } catch (e) { console.warn('Failed to load movie', id); }
        }
        for (const id of seriesIds) {
            try {
                const detail = await fetchJson(tmdbUrl(`/tv/${id}`));
                const record = normalizeSeriesRecord(detail, new Map());
                const status = statusMap[`series-${id}`] || 'wishlist';
                allItems.push({ ...record, status, _type: 'series' });
            } catch (e) { console.warn('Failed to load series', id); }
        }

        watchlistGrid.innerHTML = allItems.map(item => {
            const status = item.status || 'wishlist';
            const contentType = item._type === 'series' ? 'series' : 'movie';
            return `
                <div class="movie-card" data-status="${status}" data-content-id="${escapeHtml(item.id)}" data-content-type="${contentType}">
                    <div class="poster-container">
                        <img src="${escapeHtml(item.posterUrl || item.backdropUrl)}" alt="${escapeHtml(item.title)}" loading="lazy">
                        <span class="rating-badge">${escapeHtml(item.rating)}</span>
                        <div class="bookmark-btn"><div class="icon-wrapper" style="width: 14px; height: 14px;"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="m19 21-7-4-7 4V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v16z"/></svg></div></div>
                    </div>
                    <div class="card-info"><span class="card-title">${escapeHtml(item.title)}</span><span class="card-status">${escapeHtml(status)}</span></div>
                </div>`;
        }).join('');
    } catch (error) {
        console.warn('Unable to render watchlists page.', error);
        const watchlistGrid = document.querySelector('#page-watchlists .watchlist-grid');
        showErrorState(watchlistGrid, 'Could not load your watchlist. The backend may not be running.', () => {
            if (window.initWatchlistsPage) window.initWatchlistsPage();
        });
    }
};

window.toggleBookmark = async function(contentId, contentType) {
    const apiBaseUrl = window.API_BASE_URL || 'http://localhost:8080';
    const userId = window.appState?.userId || 1;
    try {
        await fetch(`${apiBaseUrl}/api/watchlist/add`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ userId, tmdbId: Number(contentId), contentType: contentType || 'movie', status: 'wishlist' })
        });
    } catch (e) {
        console.warn('Failed to sync bookmark', e);
    }
};

window.initWatchingPage = function() {
    const selectedContent = getSelectedContent();
    const pageTitle = document.querySelector('#page-watching .player-title');
    const pageDesc = document.querySelector('#page-watching .detail-desc');
    const episodeThumbnail = document.querySelector('#page-watching .episode-card .ep-thumbnail img');
    const episodeCards = document.querySelectorAll('#page-watching .episode-card');
    const seasonEpisodes = Array.isArray(window.appState?.currentSeasonEpisodes) ? window.appState.currentSeasonEpisodes : [];

    const fallbackTitle = selectedContent?.title || 'Now Playing';
    const fallbackDesc = selectedContent?.overview || 'Continuing live playback from the selected title.';

    if (pageTitle) {
        pageTitle.textContent = window.appState?.playerOverride?.title || fallbackTitle;
    }

    if (pageDesc) {
        pageDesc.textContent = window.appState?.playerOverride?.description || fallbackDesc;
    }

    if (episodeThumbnail && selectedContent?.posterUrl) {
        episodeThumbnail.src = selectedContent.posterUrl;
        episodeThumbnail.alt = selectedContent.title || 'Playback thumbnail';
    }

    if (selectedContent?.type === 'series' && seasonEpisodes.length > 0) {
        episodeCards.forEach((card, index) => {
            const episode = seasonEpisodes[index + 1] || seasonEpisodes[index] || null;
            if (!episode) {
                return;
            }

            const thumb = card.querySelector('.ep-thumbnail img');
            const number = card.querySelector('.ep-number');
            const title = card.querySelector('.ep-info h3');
            const desc = card.querySelector('.ep-info p');

            if (thumb) {
                const episodeImage = buildTmdbImageUrl(episode?.still_path || episode?.poster_path || '', 'w780');
                thumb.src = episodeImage || thumb.src;
                thumb.alt = episode.name || `Episode ${episode.episode_number}`;
            }

            if (number) {
                number.textContent = episode.episode_number || index + 1;
            }

            if (title) {
                title.textContent = episode.name || `Episode ${episode.episode_number}`;
            }

            if (desc) {
                desc.textContent = truncateText(episode.overview || 'Live episode details from TMDB.', 180);
            }
        });
    }
};

// Expose functions for main.js event handlers
window.renderMovieCards = renderMovieCards;
window.fetchMoviesByGenre = fetchMoviesByGenre;
window.fetchSeriesByGenre = fetchSeriesByGenre;
