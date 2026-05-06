/**
 * VozFlix search and filters
 */

window.initSearch = function() {
    const searchInputs = document.querySelectorAll('.search-box input, .filter-search input');
    let searchTimeout = null;

    const applySearch = async (rawQuery) => {
        const query = (rawQuery || '').toLowerCase().trim();

        if (!query) {
            if (document.getElementById('page-movies')?.classList.contains('active') && window._movieCatalogData) {
                renderMoviesCatalog(window._movieCatalogData);
            } else if (document.getElementById('page-series')?.classList.contains('active') && window._seriesCatalogData) {
                renderSeriesCatalog(window._seriesCatalogData);
            } else {
                document.querySelectorAll('#page-host .movie-card').forEach(card => {
                    card.dataset.searchMatch = 'true';
                    window.updateCardVisibility(card);
                });
            }
            return;
        }

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
                const genreLookup = new Map();

                if (isSeriesPage) {
                    const items = rawResults.map(r => normalizeSeriesRecord(r, genreLookup));
                    const seriesGrids = document.querySelectorAll('#page-series .movie-grid');
                    if (seriesGrids.length > 0) {
                        seriesGrids[0].innerHTML = '';
                        if (seriesGrids[1]) seriesGrids[1].innerHTML = '';
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
                    const grid = document.querySelector('#page-host .movie-grid');
                    if (grid) {
                        grid.innerHTML = '';
                        const items = rawResults.map(r => r.media_type === 'tv' ? normalizeSeriesRecord(r, genreLookup) : normalizeMovieRecord(r, genreLookup));
                        renderMovieCards(grid, items, { showBookmark: true });
                    }
                }
            } catch (error) {
                console.error('Search failed', error);
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
