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

    const applySearch = (rawQuery) => {
        const query = (rawQuery || '').toLowerCase().trim();
        const cards = document.querySelectorAll('#page-host .movie-card');

        cards.forEach(card => {
            const title = (card.querySelector('.card-title')?.innerText || '').toLowerCase();
            const status = (card.querySelector('.card-status')?.innerText || '').toLowerCase();
            const year = deriveCardYear(card);
            const type = deriveCardType(card);
            const genres = deriveCardGenres(card).join(' ');
            const haystack = `${title} ${status} ${year} ${type} ${genres}`;

            card.dataset.searchMatch = !query || haystack.includes(query) ? 'true' : 'false';
            window.updateCardVisibility(card);
        });
    };

    searchInputs.forEach(input => {
        if (input.dataset.searchBound === 'true') return;
        input.dataset.searchBound = 'true';
        input.addEventListener('input', (e) => applySearch(e.target.value));
    });

    const initialValue = Array.from(searchInputs).find(input => input.value)?.value || '';
    applySearch(initialValue);
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
