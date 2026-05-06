/**
 * VozFlix watchlist and bookmark actions
 */

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
            } catch (error) {
                console.warn('Failed to load movie', id);
            }
        }
        for (const id of seriesIds) {
            try {
                const detail = await fetchJson(tmdbUrl(`/tv/${id}`));
                const record = normalizeSeriesRecord(detail, new Map());
                const status = statusMap[`series-${id}`] || 'wishlist';
                allItems.push({ ...record, status, _type: 'series' });
            } catch (error) {
                console.warn('Failed to load series', id);
            }
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
    } catch (error) {
        console.warn('Failed to sync bookmark', error);
    }
};
