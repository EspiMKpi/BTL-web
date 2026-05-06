/**
 * VozFlix detail, episode, and watching actions
 */

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
    if (!seasonTabs) return [];

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
    if (!episodeGrid) return;

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

async function loadDetailSeason(contentId, seasonNumber) {
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

    try {
        await loadDetailSeason(selectedContent.id, seasonNumber);
    } catch (error) {
        console.warn('Unable to load season episodes.', error);
    }
};

window.initDetailPage = async function() {
    showGlobalLoading('Loading details...');
    const selectedContent = getSelectedContent();

    if (!selectedContent || !selectedContent.id) {
        hideGlobalLoading();
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

        if (heroTitle) heroTitle.textContent = title;
        if (heroDesc) heroDesc.textContent = overview;

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
            if (synopsisCopy) synopsisCopy.textContent = overview;
        }
        if (infoCards[1]) {
            const castCopy = infoCards[1].querySelector('p:last-child');
            if (castCopy) castCopy.textContent = formatCastList(credits?.cast);
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
                await loadDetailSeason(selectedContent.id, initialSeasonNumber);
            }
        } else if (episodeSection) {
            episodeSection.style.display = 'none';
        }

        window.appState.playerOverride = { title, description: overview };
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

window.initWatchingPage = function() {
    const selectedContent = getSelectedContent();
    const pageTitle = document.querySelector('#page-watching .player-title');
    const pageDesc = document.querySelector('#page-watching .detail-desc');
    const episodeThumbnail = document.querySelector('#page-watching .episode-card .ep-thumbnail img');
    const episodeCards = document.querySelectorAll('#page-watching .episode-card');
    const seasonEpisodes = Array.isArray(window.appState?.currentSeasonEpisodes) ? window.appState.currentSeasonEpisodes : [];

    const fallbackTitle = selectedContent?.title || 'Now Playing';
    const fallbackDesc = selectedContent?.overview || 'Continuing live playback from the selected title.';

    if (pageTitle) pageTitle.textContent = window.appState?.playerOverride?.title || fallbackTitle;
    if (pageDesc) pageDesc.textContent = window.appState?.playerOverride?.description || fallbackDesc;

    if (episodeThumbnail && selectedContent?.posterUrl) {
        episodeThumbnail.src = selectedContent.posterUrl;
        episodeThumbnail.alt = selectedContent.title || 'Playback thumbnail';
    }

    if (selectedContent?.type === 'series' && seasonEpisodes.length > 0) {
        episodeCards.forEach((card, index) => {
            const episode = seasonEpisodes[index + 1] || seasonEpisodes[index] || null;
            if (!episode) return;

            const thumb = card.querySelector('.ep-thumbnail img');
            const number = card.querySelector('.ep-number');
            const title = card.querySelector('.ep-info h3');
            const desc = card.querySelector('.ep-info p');

            if (thumb) {
                const episodeImage = buildTmdbImageUrl(episode?.still_path || episode?.poster_path || '', 'w780');
                thumb.src = episodeImage || thumb.src;
                thumb.alt = episode.name || `Episode ${episode.episode_number}`;
            }
            if (number) number.textContent = episode.episode_number || index + 1;
            if (title) title.textContent = episode.name || `Episode ${episode.episode_number}`;
            if (desc) desc.textContent = truncateText(episode.overview || 'Live episode details from TMDB.', 180);
        });
    }
};
