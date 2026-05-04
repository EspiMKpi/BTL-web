/**
 * VozFlix Main
 * Application entry point and event delegation
 */

document.addEventListener('DOMContentLoaded', () => {
    if (window.ensureGuestSession) window.ensureGuestSession();
    window.onPageRendered = (pageId) => {
        if (window.updateProfileDisplay) window.updateProfileDisplay();
        if (window.initSearch) window.initSearch();
        if (window.initFilters) window.initFilters();
        if (pageId === 'discover' || pageId === 'movies' || pageId === 'series') {
            if (window.initCatalogPage) window.initCatalogPage(pageId);
        } else if (pageId === 'detail') {
            if (window.initDetailPage) window.initDetailPage();
        } else if (pageId === 'profile') {
            if (window.initProfilePage) window.initProfilePage();
        } else if (pageId === 'watchlists') {
            if (window.initWatchlistsPage) window.initWatchlistsPage();
        } else if (pageId === 'watching') {
            if (window.initWatchingPage) window.initWatchingPage();
        }
    };

    if (window.bootstrapRouter) {
        window.bootstrapRouter();
    }

    // --- Global Click Interactivity ---
    document.addEventListener('click', (e) => {
        // 0. Navigation links -> Route to page
        const navLink = e.target.closest('.nav-link');
        if (navLink) {
            e.preventDefault();
            const targetPage = navLink.getAttribute('data-page');
            if (targetPage && window.switchPage) {
                window.switchPage(targetPage);
            }
            return;
        }

        // 0b. Profile dropdown links -> Route to profile or settings
        const profileLink = e.target.closest('#profile-link, #settings-link');
        if (profileLink) {
            e.preventDefault();
            const target = profileLink.id === 'settings-link' ? 'settings' : 'profile';
            const token = localStorage.getItem('jwt_token');
            if (!token) {
                window.appState = window.appState || {};
                window.appState.redirectAfterLogin = target;
                window.switchPage('login');
                return;
            }
            window.switchPage(target);
            return;
        }

        // 1. Movie Card Click -> Go to Detail
        const movieCard = e.target.closest('.movie-card');
        if (movieCard && !e.target.closest('.bookmark-btn') && !e.target.closest('.episode-card')) {
            const contentId = movieCard.getAttribute('data-content-id') || movieCard.getAttribute('data-movie-id');
            const contentType = movieCard.getAttribute('data-content-type') || movieCard.getAttribute('data-type') || 'movie';
            const title = movieCard.querySelector('.card-title')?.innerText || 'Untitled';
            const overview = movieCard.querySelector('.card-status')?.innerText || '';

            window.appState = window.appState || {};
            window.appState.selectedContent = {
                id: contentId ? Number(contentId) : null,
                type: contentType,
                title,
                overview,
                year: movieCard.getAttribute('data-year') || '',
                genreText: movieCard.getAttribute('data-genre') || '',
                rating: movieCard.querySelector('.rating-badge')?.innerText || '',
                posterUrl: movieCard.querySelector('img')?.src || '',
                backdropUrl: movieCard.querySelector('img')?.src || ''
            };
            window.appState.playerOverride = {
                title,
                description: overview
            };
            window.switchPage('detail');
            return;
        }

        // 2. Watch Now Button or Episode Card -> Go to Watching
        const epCard = e.target.closest('.episode-card');
        const watchBtn = e.target.closest('#btn-watch-now') || e.target.closest('.hero .btn-primary') || epCard;
        
        if (watchBtn) {
            if (epCard) {
                window.appState = window.appState || {};
                const epTitle = epCard.querySelector('h3').innerText;
                const epDesc = epCard.querySelector('p').innerText;
                window.appState.playerOverride = {
                    title: epTitle,
                    description: epDesc
                };
            } else if (window.appState) {
                window.appState.playerOverride = null;
            }
            window.switchPage('watching');
            return;
        }

        // 3. Login Button -> Go to Discover
        const loginBtn = e.target.closest('#btn-login-continue');
        if (loginBtn) {
            e.preventDefault();
            const email = document.getElementById('login-email').value;
            const password = document.getElementById('login-password').value;
            
            if (!email || !password) {
                window.showNotification('Please enter email and password');
                return;
            }
            
            loginBtn.innerText = 'Signing in...';
            loginBtn.disabled = true;
            
            fetch(buildApiUrl('/api/auth/login'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            })
            .then(res => res.json().then(data => ({ status: res.status, data })))
            .then(res => {
                loginBtn.innerText = 'Continue';
                loginBtn.disabled = false;
                
                if (res.status === 200 && res.data.token) {
                    window.authenticate(res.data.token, res.data);
                    if (window.appState) window.appState.playerOverride = null;
                    const next = window.appState?.redirectAfterLogin || 'discover';
                    window.switchPage(next);
                } else {
                    window.showNotification(res.data.error || 'Login failed');
                }
            })
            .catch(err => {
                loginBtn.innerText = 'Continue';
                loginBtn.disabled = false;
                window.showNotification('Login failed. Please try again.');
            });
            return;
        }

        // 3b. Register Button -> Go to Discover
        const registerBtn = e.target.closest('#btn-register-continue');
        if (registerBtn) {
            e.preventDefault();
            const username = document.getElementById('register-username').value;
            const email = document.getElementById('register-email').value;
            const password = document.getElementById('register-password').value;
            const confirm = document.getElementById('register-confirm').value;
            
            if (!username || !email || !password) {
                window.showNotification('Please fill all fields');
                return;
            }
            if (password !== confirm) {
                window.showNotification('Passwords do not match');
                return;
            }
            
            registerBtn.innerText = 'Creating account...';
            registerBtn.disabled = true;
            
            fetch(buildApiUrl('/api/auth/register'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, email, password })
            })
            .then(res => res.json().then(data => ({ status: res.status, data })))
            .then(res => {
                registerBtn.innerText = 'Create account';
                registerBtn.disabled = false;
                
                if (res.status === 200 && res.data.token) {
                    window.authenticate(res.data.token, res.data);
                    if (window.appState) window.appState.playerOverride = null;
                    const next = window.appState?.redirectAfterLogin || 'discover';
                    window.switchPage(next);
                } else {
                    window.showNotification(res.data.error || 'Registration failed');
                }
            })
            .catch(err => {
                registerBtn.innerText = 'Create account';
                registerBtn.disabled = false;
                window.showNotification('Registration failed. Please try again.');
            });
            return;
        }

        // 3c. Auth navigation (Login <-> Register)
        const toRegister = e.target.closest('#link-to-register');
        if (toRegister) { e.preventDefault(); window.switchPage('register'); return; }

        const toLogin = e.target.closest('#link-to-login');
        if (toLogin) { e.preventDefault(); window.switchPage('login'); return; }

        // 4. Avatar Toggle -> Open Dropdown
        const avatarToggle = e.target.closest('#avatar-toggle');
        const dropdown = document.getElementById('profile-dropdown');
        if (avatarToggle && dropdown) {
            const userInfoRaw = localStorage.getItem('user_info');
            if (userInfoRaw) {
                try {
                    const userInfo = JSON.parse(userInfoRaw);
                    const nameEl = dropdown.querySelector('.dropdown-name');
                    const handleEl = dropdown.querySelector('.dropdown-handle');
                    const name = userInfo.username || userInfo.email || 'User';
                    const handleBase = userInfo.username || (userInfo.email ? userInfo.email.split('@')[0] : 'user');
                    if (nameEl) nameEl.textContent = name;
                    if (handleEl) handleEl.textContent = '@' + handleBase;
                } catch(e) {}
            }
            dropdown.classList.toggle('show');
            return;
        }

        // 5. Logout Button -> Go to Login
        const logoutBtn = e.target.closest('#logout-btn');
        if (logoutBtn) {
            window.logout();
            return;
        }

        // 6. Click Outside Dropdown -> Close it
        if (dropdown && dropdown.classList.contains('show') && !e.target.closest('.avatar-wrapper')) {
            dropdown.classList.remove('show');
        }

        // 6b. Mobile Menu Toggle
        const mobileMenuBtn = e.target.closest('#mobile-menu-btn');
        if (mobileMenuBtn) {
            const navLinksContainer = document.querySelector('.nav-links');
            if (navLinksContainer) navLinksContainer.classList.toggle('active');
        }

        // 7. Bookmarking Logic
        const bookmarkBtn = e.target.closest('.bookmark-btn');
        if (bookmarkBtn) {
            bookmarkBtn.classList.toggle('active');
            const card = bookmarkBtn.closest('.movie-card');
            const contentId = card?.getAttribute('data-content-id');
            const contentType = card?.getAttribute('data-content-type') || 'movie';
            const icon = bookmarkBtn.querySelector('svg');
            if (bookmarkBtn.classList.contains('active')) {
                bookmarkBtn.style.background = 'var(--accent-gold)';
                if (icon) icon.style.fill = 'black';
                window.showNotification("Added to Watchlist!");
                if (contentId && typeof window.toggleBookmark === 'function') {
                    window.toggleBookmark(contentId, contentType);
                }
            } else {
                bookmarkBtn.style.background = 'rgba(122, 120, 128, 0.5)';
                if (icon) icon.style.fill = 'none';
                window.showNotification("Removed from Watchlist.");
            }
        }

        // 8. Generic Tab/Chip Switching (filter-chip on series page)
        const chip = e.target.closest('.filter-chip');
        if (chip) {
            chip.parentElement.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('active'));
            chip.classList.add('active');

            // Series page genre filter - fetch from TMDB
            const genreId = chip.dataset.genreId;
            const seriesGrids = document.querySelectorAll('#page-series .movie-grid');
            if (seriesGrids.length > 0) {
                const targetGrid = seriesGrids[0];
                if (!genreId || chip.textContent.trim() === 'All') {
                    // Restore original catalog
                    if (window._seriesCatalogData && typeof window.renderMovieCards === 'function') {
                        const catalog = window._seriesCatalogData;
                        const allSeries = (catalog.popular.length > 0 ? catalog.popular : catalog.topRated).slice(0, 15);
                        const TMDB_IMAGE_BASE_URL = 'https://image.tmdb.org/t/p';
                        const normalized = allSeries.map(s => ({
                            id: s.id, title: s.name || s.title || 'Untitled', overview: s.overview || '',
                            year: (s.first_air_date || '').slice(0, 4), genres: [], genreText: '',
                            rating: Number.isFinite(Number(s.vote_average)) ? Number(s.vote_average).toFixed(1) : 'N/A',
                            posterUrl: (s.poster_path || s.backdrop_path) ? TMDB_IMAGE_BASE_URL + '/w500' + (s.poster_path || s.backdrop_path) : '',
                            backdropUrl: (s.backdrop_path || s.poster_path) ? TMDB_IMAGE_BASE_URL + '/w1280' + (s.backdrop_path || s.poster_path) : '',
                            status: (s.first_air_date || '').slice(0, 4)
                        }));
                        window.renderMovieCards(targetGrid, normalized, { showBookmark: true, type: 'series' });
                    }
                } else if (typeof window.fetchSeriesByGenre === 'function') {
                    targetGrid.innerHTML = '<div class="vf-loading"><div class="vf-spinner"></div><p>Loading series...</p></div>';
                    window.fetchSeriesByGenre(genreId, 1).then(series => {
                        const TMDB_IMAGE_BASE_URL = 'https://image.tmdb.org/t/p';
                        const normalized = series.slice(0, 50).map(s => ({
                            id: s.id, title: s.name || s.title || 'Untitled', overview: s.overview || '',
                            year: (s.first_air_date || '').slice(0, 4), genres: [], genreText: '',
                            rating: Number.isFinite(Number(s.vote_average)) ? Number(s.vote_average).toFixed(1) : 'N/A',
                            posterUrl: (s.poster_path || s.backdrop_path) ? TMDB_IMAGE_BASE_URL + '/w500' + (s.poster_path || s.backdrop_path) : '',
                            backdropUrl: (s.backdrop_path || s.poster_path) ? TMDB_IMAGE_BASE_URL + '/w1280' + (s.backdrop_path || s.poster_path) : '',
                            status: (s.first_air_date || '').slice(0, 4)
                        }));
                        if (typeof window.renderMovieCards === 'function') window.renderMovieCards(targetGrid, normalized, { showBookmark: true, type: 'series' });
                    }).catch(() => {
                        targetGrid.innerHTML = '<div class="vf-error"><h3>Failed to load</h3><p>Could not fetch series for this genre.</p></div>';
                    });
                }
            }
        }

        // 8b. Discover genre chip click
        const genreChip = e.target.closest('.genre-chip');
        if (genreChip && document.getElementById('discover-genre-chips')?.contains(genreChip)) {
            document.querySelectorAll('#discover-genre-chips .genre-chip').forEach(c => c.classList.remove('active'));
            genreChip.classList.add('active');
            const genreId = genreChip.dataset.genreId;
            const resultsGrid = document.getElementById('discover-genre-results');
            if (genreId === 'all' || !genreId) {
                if (resultsGrid) resultsGrid.style.display = 'none';
            } else if (resultsGrid && typeof window.fetchMoviesByGenre === 'function') {
                resultsGrid.style.display = '';
                resultsGrid.innerHTML = '<div class="vf-loading"><div class="vf-spinner"></div><p>Fetching movies...</p></div>';
                window.fetchMoviesByGenre(genreId, 1).then(movies => {
                    const state = window._discoverState;
                    const genreMap = state?.movieCatalog?.genreMap || new Map();
                    const normalized = movies.slice(0, 50).map(m => {
                        const rd = m.release_date || '';
                        const year = rd ? rd.slice(0, 4) : '';
                        const posterPath = m.poster_path || m.backdrop_path || '';
                        const backdropPath = m.backdrop_path || m.poster_path || '';
                        const TMDB_IMAGE_BASE_URL = 'https://image.tmdb.org/t/p';
                        return {
                            id: m.id, title: m.title || 'Untitled', overview: m.overview || '',
                            year, genres: [], genreText: '',
                            rating: Number.isFinite(Number(m.vote_average)) ? Number(m.vote_average).toFixed(1) : 'N/A',
                            posterUrl: posterPath ? TMDB_IMAGE_BASE_URL + '/w500' + posterPath : '',
                            backdropUrl: backdropPath ? TMDB_IMAGE_BASE_URL + '/w1280' + backdropPath : '',
                            status: year
                        };
                    });
                    if (typeof window.renderMovieCards === 'function') window.renderMovieCards(resultsGrid, normalized, { showBookmark: true });
                }).catch(err => {
                    console.error('Genre fetch failed', err);
                    resultsGrid.innerHTML = '<div class="vf-error"><h3>Failed to load</h3><p>Could not fetch movies for this genre.</p></div>';
                });
            }
        }

        const tab = e.target.closest('.list-tab, .season-tab');
        if (tab) {
            tab.parentElement.querySelectorAll('.list-tab, .season-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            
            // Trigger specific action if list tab
            const watchlistGrid = document.querySelector('.watchlist-grid');
            if (tab.classList.contains('list-tab') && watchlistGrid) {
                const filterValue = (tab.dataset.filter || tab.innerText || '').toLowerCase().trim();
                const cards = watchlistGrid.querySelectorAll('.movie-card');
                cards.forEach(card => {
                    const status = (card.dataset.status || card.querySelector('.card-status')?.innerText || '').toLowerCase();
                    const isMatch = filterValue === 'all' || status.includes(filterValue);
                    card.dataset.listMatch = isMatch ? 'true' : 'false';

                    if (window.updateCardVisibility) {
                        window.updateCardVisibility(card);
                    } else {
                        card.style.display = isMatch ? '' : 'none';
                    }
                });
            }

            if (tab.classList.contains('season-tab') && typeof window.loadSeasonEpisodes === 'function') {
                const seasonNumber = Number.parseInt(tab.getAttribute('data-season-number') || tab.innerText.replace(/[^0-9]/g, ''), 10);
                if (Number.isFinite(seasonNumber)) {
                    window.loadSeasonEpisodes(seasonNumber);
                }
            }
        }

        // 9. Discover FAQ accordion toggle
        const faqQuestion = e.target.closest('.nf-faq-question');
        if (faqQuestion) {
            const faqItem = faqQuestion.closest('.nf-faq-item');
            if (!faqItem) return;

            const isOpen = faqItem.classList.contains('open');
            const allFaqItems = document.querySelectorAll('.nf-faq-item');
            allFaqItems.forEach(item => {
                item.classList.remove('open');
                const button = item.querySelector('.nf-faq-question');
                if (button) button.setAttribute('aria-expanded', 'false');
            });

            if (!isOpen) {
                faqItem.classList.add('open');
                faqQuestion.setAttribute('aria-expanded', 'true');
            }
        }
    });

    // Sort dropdown handler for Movies page
    document.addEventListener('change', (e) => {
        const sortSelect = e.target.closest('#movies-sort-select');
        if (!sortSelect) return;
        const sortValue = sortSelect.value;
        const cards = window._moviesAllCards;
        if (!cards) return;

        let sorted = [...cards];
        if (sortValue === 'rating') {
            sorted.sort((a, b) => parseFloat(b.rating) - parseFloat(a.rating));
        } else if (sortValue === 'title') {
            sorted.sort((a, b) => (a.title || '').localeCompare(b.title || ''));
        } else if (sortValue === 'year-desc') {
            sorted.sort((a, b) => (b.year || '').localeCompare(a.year || ''));
        } else if (sortValue === 'year-asc') {
            sorted.sort((a, b) => (a.year || '').localeCompare(b.year || ''));
        } else {
            // popularity (default order)
        }

        // Apply genre filter on top of sort
        const checkedGenres = Array.from(document.querySelectorAll('#movies-filter-genres input:checked')).map(i => i.value);
        if (checkedGenres.length > 0) {
            sorted = sorted.filter(m => {
                const movieGenres = (m.genres || []).map(g => g.toLowerCase());
                return checkedGenres.some(cg => movieGenres.includes(cg));
            });
        }

        const grid = document.querySelector('#page-movies #search-results-grid');
        if (grid && typeof window.renderMovieCards === 'function') {
            window.renderMovieCards(grid, sorted, { showBookmark: true });
        }
    });

    // Genre checkbox filter for Movies page
    document.addEventListener('change', (e) => {
        if (!e.target.closest('#movies-filter-genres input')) return;
        const sortSelect = document.getElementById('movies-sort-select');
        if (sortSelect) {
            sortSelect.dispatchEvent(new Event('change', { bubbles: true }));
        } else {
            // No sort select, just filter
            const cards = window._moviesAllCards;
            if (!cards) return;
            const checkedGenres = Array.from(document.querySelectorAll('#movies-filter-genres input:checked')).map(i => i.value);
            let filtered = [...cards];
            if (checkedGenres.length > 0) {
                filtered = filtered.filter(m => {
                    const movieGenres = (m.genres || []).map(g => g.toLowerCase());
                    return checkedGenres.some(cg => movieGenres.includes(cg));
                });
            }
            const grid = document.querySelector('#page-movies #search-results-grid');
            if (grid && typeof window.renderMovieCards === 'function') {
                window.renderMovieCards(grid, filtered, { showBookmark: true });
            }
        }
    });
});
