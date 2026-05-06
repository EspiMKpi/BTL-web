/**
 * VozFlix catalog actions
 */

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
    if (kicker) kicker.textContent = movie.year ? `${movie.year} Spotlight` : 'Featured Movie';
    if (title) title.textContent = movie.title;
    if (copy) copy.textContent = truncateText(movie.overview || 'Browse the latest movies and series pulled from TMDB.', 180);
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
    if (title) title.textContent = movie.title;
    if (copy) copy.textContent = truncateText(movie.overview || 'Discover the latest movies from TMDB, ready to browse by search or filter.', 180);

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
    if (title) title.textContent = series.title;
    if (copy) copy.textContent = truncateText(series.overview || 'Stream live series and mini-series with poster art pulled from TMDB.', 180);

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

function fetchMultiPageResults(endpoint, pages, extraParams = {}) {
    const requests = [];
    for (let page = 1; page <= pages; page++) {
        requests.push(fetchJson(buildApiUrl(endpoint, { page, ...extraParams })));
    }
    return Promise.all(requests).then(responses => responses.flatMap(response => Array.isArray(response?.results) ? response.results : []));
}

async function fetchMoviePageCatalog() {
    const pages = 3;
    const [popular, topRated, nowPlaying, genreMap] = await Promise.all([
        fetchMultiPageResults('/api/movies/popular', pages),
        fetchMultiPageResults('/api/movies/top-rated', pages),
        fetchMultiPageResults('/api/movies/now-playing', pages),
        fetchJson(backendUrl('/api/movies/genres')).then(response => {
            const genres = Array.isArray(response?.genres) ? response.genres : [];
            const genreMap = new Map();
            genres.forEach(genre => {
                if (genre?.id != null && genre?.name) genreMap.set(Number(genre.id), genre.name);
            });
            return genreMap;
        }),
    ]);

    return { popular, topRated, nowPlaying, genreMap };
}

async function fetchSeriesPageCatalog() {
    const pages = 3;
    const [popular, topRated, genreMap] = await Promise.all([
        fetchMultiPageResults('/api/series/popular', pages),
        fetchMultiPageResults('/api/series/top-rated', pages),
        fetchJson(backendUrl('/api/series/genres')).then(response => {
            const genres = Array.isArray(response?.genres) ? response.genres : [];
            const genreMap = new Map();
            genres.forEach(genre => {
                if (genre?.id != null && genre?.name) genreMap.set(Number(genre.id), genre.name);
            });
            return genreMap;
        }),
    ]);

    return { popular, topRated, genreMap };
}

window.fetchMoviesByGenre = async function(genreId, page) {
    const response = await fetchJson(backendUrl('/api/movies/discover', { with_genres: genreId, page: page || 1, sort_by: 'popularity.desc' }));
    return Array.isArray(response?.results) ? response.results : [];
};

window.fetchSeriesByGenre = async function(genreId, page) {
    const response = await fetchJson(backendUrl('/api/series/discover', { with_genres: genreId, page: page || 1, sort_by: 'popularity.desc' }));
    return Array.isArray(response?.results) ? response.results : [];
};

function renderDiscoverCatalog(movieCatalog, seriesCatalog) {
    const heroMovie = normalizeMovieRecord(movieCatalog.nowPlaying[0] || movieCatalog.popular[0] || movieCatalog.topRated[0], movieCatalog.genreMap);

    const genreChipsContainer = document.getElementById('discover-genre-chips');
    if (genreChipsContainer && movieCatalog.genreMap) {
        const allGenres = Array.from(movieCatalog.genreMap.entries());
        genreChipsContainer.innerHTML = '<button class="genre-chip active" data-genre-id="all">All</button>' +
            allGenres.map(([id, name]) => `<button class="genre-chip" data-genre-id="${id}">${escapeHtml(name)}</button>`).join('');
        window._discoverState = { movieCatalog, seriesCatalog };
    }

    const top10Movies = movieCatalog.popular.slice(0, 10).map(movie => normalizeMovieRecord(movie, movieCatalog.genreMap));
    const trendingMovies = (movieCatalog.nowPlaying.length > 0 ? movieCatalog.nowPlaying : movieCatalog.popular).slice(0, 15).map(movie => normalizeMovieRecord(movie, movieCatalog.genreMap));
    const originalsSeries = (seriesCatalog?.topRated?.length > 0 ? seriesCatalog.topRated : seriesCatalog?.popular || []).slice(0, 15).map(series => normalizeSeriesRecord(series, seriesCatalog.genreMap));

    if (heroMovie.id) applyDiscoverHero(heroMovie);

    const top10Title = document.getElementById('discover-top10-title');
    const trendingTitle = document.getElementById('discover-trending-title');
    const seriesTitle = document.getElementById('discover-series-title');
    if (top10Title) top10Title.textContent = 'Top 10 in Vietnam Today';
    if (trendingTitle) trendingTitle.textContent = heroMovie.title ? `${heroMovie.title} & Trending` : 'Trending Now';
    if (seriesTitle) seriesTitle.textContent = originalsSeries.length > 0 ? 'Featured Series' : 'Popular Series';

    renderMovieCards(document.querySelector('#page-discover .nf-top10-grid'), top10Movies, { top10: true });
    renderMovieCards(document.querySelector('#page-discover #discover-trending-grid'), trendingMovies);
    renderMovieCards(document.querySelector('#page-discover #discover-series-grid'), originalsSeries, { type: 'series' });
}

function renderMoviesCatalog(catalog) {
    const heroMovie = normalizeMovieRecord(catalog.popular[0] || catalog.topRated[0] || catalog.nowPlaying[0], catalog.genreMap);
    const movieRows = (catalog.popular.length > 0 ? catalog.popular : catalog.topRated).slice(0, 50).map(movie => normalizeMovieRecord(movie, catalog.genreMap));

    if (heroMovie.id) applyMoviesHero(heroMovie);

    const titleEl = document.getElementById('movies-catalog-title');
    const copyEl = document.getElementById('movies-catalog-copy');
    if (titleEl) titleEl.textContent = heroMovie.title || 'Movies';
    if (copyEl) copyEl.textContent = truncateText(heroMovie.overview || 'Browse the full movie catalog.', 180);

    const metricRating = document.querySelector('#movies-metric-rating span');
    const metricCount = document.querySelector('#movies-metric-count span');
    if (metricRating) metricRating.textContent = heroMovie.rating;
    if (metricCount) metricCount.textContent = movieRows.length;

    renderGenreFilters('movies-filter-genres', catalog.genreMap, 'genre');
    window._moviesCatalogData = catalog;
    window._moviesAllCards = (catalog.popular.length > 0 ? catalog.popular : catalog.topRated).slice(0, 50).map(m => normalizeMovieRecord(m, catalog.genreMap));

    const filterBar = document.querySelector('#page-movies .filter-bar');
    if (filterBar && !document.getElementById('movies-sort-select')) {
        const sortHtml = '<select class="sort-select" id="movies-sort-select"><option value="popularity">Popular</option><option value="rating">Top Rated</option><option value="title">A-Z</option><option value="year-desc">Newest</option><option value="year-asc">Oldest</option></select>';
        filterBar.insertAdjacentHTML('beforeend', sortHtml);
    }

    renderMovieCards(document.querySelector('#page-movies #search-results-grid'), movieRows, { showBookmark: true });
    if (window.initSearch) window.initSearch();
    if (window.initFilters) window.initFilters();
}

function renderSeriesCatalog(catalog) {
    const heroSeries = normalizeSeriesRecord(catalog.popular[0] || catalog.topRated[0], catalog.genreMap);
    const trendingSeries = (catalog.popular.length > 0 ? catalog.popular : catalog.topRated).slice(0, 15).map(series => normalizeSeriesRecord(series, catalog.genreMap));
    const miniSeries = (catalog.topRated.length > 0 ? catalog.topRated : catalog.popular).slice(0, 15).map(series => normalizeSeriesRecord(series, catalog.genreMap));
    const seriesGrids = document.querySelectorAll('#page-series .movie-grid');

    if (heroSeries.id) applySeriesHero(heroSeries);

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
        filtersContainer.innerHTML = '<button class="filter-chip active">All</button>' + genres.map(([id, name]) => `<button class="filter-chip" data-genre-id="${id}">${escapeHtml(name)}</button>`).join('');
    }

    if (seriesGrids[0]) renderMovieCards(seriesGrids[0], trendingSeries, { showBookmark: true, type: 'series' });
    if (seriesGrids[1]) renderMovieCards(seriesGrids[1], miniSeries, { showBookmark: true, type: 'series' });
    window._seriesCatalogData = catalog;
}

window.initCatalogPage = async function(pageId) {
    if (pageId !== 'discover' && pageId !== 'movies' && pageId !== 'series') {
        return;
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
            if (window.appState.catalogRenderToken !== renderToken) return;
            renderDiscoverCatalog(movieCatalog, seriesCatalog);
        } else if (pageId === 'movies') {
            const catalog = await fetchMoviePageCatalog(apiBaseUrl);
            if (window.appState.catalogRenderToken !== renderToken) return;
            renderMoviesCatalog(catalog);
        } else if (pageId === 'series') {
            const catalog = await fetchSeriesPageCatalog(apiBaseUrl);
            if (window.appState.catalogRenderToken !== renderToken) return;
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
