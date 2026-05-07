/**
 * VozFlix Main
 * Application entry point with Alpine.js reactivity + API integration
 */

import Alpine from 'alpinejs';
import { pages_ready } from './pages.js';
import { switchPage } from './router.js';
import { showNotification, initSearch, initFilters } from './actions.js';
import {
    getHomeRails, getGenres, browseGenre, searchContent,
    getMovieDetail, getSeriesDetail,
    getWatchlist, addToWatchlist, updateWatchlistItem, removeFromWatchlist,
    getContinueWatching, updateProgress,
    getRatings, getMyRatings, createRating, deleteRating,
    getProfile, getProfileStats, updateProfile,
    posterUrl, backdropUrl, formatRuntime, formatDate, genreString,
} from './api.js';

// Make Alpine available globally
window.Alpine = Alpine;

// --- Alpine Stores ---
Alpine.store('toast', {
    message: '',
    visible: false,
    show(msg) {
        this.message = msg;
        this.visible = true;
        setTimeout(() => { this.visible = false; }, 3000);
    }
});

Alpine.store('auth', {
    user: null,
    token: localStorage.getItem('token'),
    get isLoggedIn() { return !!this.token; },

    async login(email, password) {
        const res = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || data.error || 'Login failed');
        this.token = data.token;
        this.user = data.user;
        localStorage.setItem('token', data.token);
        return data;
    },

    async register(email, password) {
        const res = await fetch('/api/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || data.error || 'Registration failed');
        this.token = data.token;
        this.user = data.user;
        localStorage.setItem('token', data.token);
        return data;
    },

    logout() {
        this.token = null;
        this.user = null;
        localStorage.removeItem('token');
    },

    async fetchUser() {
        if (!this.token) return;
        try {
            const res = await fetch('/api/auth/me', {
                headers: { 'Authorization': `Bearer ${this.token}` }
            });
            if (res.ok) {
                this.user = await res.json();
            } else {
                this.logout();
            }
        } catch { this.logout(); }
    }
});

// --- Alpine Components ---
Alpine.data('appState', () => ({
    init() {
        Alpine.store('auth').fetchUser();
    }
}));

Alpine.data('loginForm', () => ({
    email: '',
    password: '',
    loading: false,
    error: '',
    async submit() {
        this.loading = true;
        this.error = '';
        try {
            await Alpine.store('auth').login(this.email, this.password);
            switchPage('discover');
            Alpine.store('content').loadHome();
        } catch (e) {
            this.error = e.message;
        } finally {
            this.loading = false;
        }
    }
}));

Alpine.data('registerForm', () => ({
    email: '',
    password: '',
    confirm: '',
    loading: false,
    error: '',
    async submit() {
        if (this.password !== this.confirm) {
            this.error = 'Passwords do not match';
            return;
        }
        this.loading = true;
        this.error = '';
        try {
            await Alpine.store('auth').register(this.email, this.password);
            switchPage('discover');
            Alpine.store('content').loadHome();
        } catch (e) {
            this.error = e.message;
        } finally {
            this.loading = false;
        }
    }
}));

Alpine.data('dropdown', () => ({
    open: false,
    toggle() { this.open = !this.open; },
    close() { this.open = false; }
}));

Alpine.data('filterPanel', () => ({
    open: false,
    toggle() { this.open = !this.open; }
}));

Alpine.data('faqItem', () => ({
    open: false,
    toggle() { this.open = !this.open; }
}));

// ── Discover Page Component ──────────────────────────────────────────────
Alpine.data('discoverPage', () => ({
    rails: [],
    loading: false,

    async init() {
        this.loading = true;
        try {
            const data = await getHomeRails(10);
            this.rails = data.rails || [];
        } catch (e) {
            console.error('Failed to load home rails:', e);
        } finally {
            this.loading = false;
        }
    },

    posterUrl(path) {
        return posterUrl(path, 'w500');
    },

    formatItemStatus(item, contentType) {
        if (contentType === 'series' || item.name) {
            const seasons = item.number_of_seasons;
            if (seasons) return `${seasons} Season${seasons > 1 ? 's' : ''}`;
            return 'Series';
        }
        const year = item.release_date ? item.release_date.substring(0, 4) : '';
        const genres = item.genres?.map(g => g.name).slice(0, 2).join(', ') || '';
        return [year, genres].filter(Boolean).join(' · ');
    }
}));

// ── Detail Page Component ────────────────────────────────────────────────
Alpine.data('detailPage', () => ({
    showEpisodes: false,
    activeSeason: 1,

    init() {
        // Reset state when navigating to detail
        this.showEpisodes = false;
        this.activeSeason = 1;
    },

    get inWatchlist() {
        const item = this.$store.detail.item;
        if (!item) return false;
        return this.$store.watchlist.isBookmarked(item.tmdb_id);
    },

    async toggleWatchlist() {
        const item = this.$store.detail.item;
        if (!item) return;
        const contentType = this.$store.detail.type;
        const tmdbId = item.tmdb_id;
        const existing = this.$store.watchlist.getItemByTmdbId(tmdbId);
        if (existing) {
            await this.$store.watchlist.removeItem(existing._id);
        } else {
            await this.$store.watchlist.addItem(contentType, tmdbId);
        }
    }
}));

// ── Watchlist Page Component ─────────────────────────────────────────────
Alpine.data('watchlistPage', () => ({
    activeTab: 'all',
    searchQuery: '',

    get filteredItems() {
        let items = this.$store.watchlist.items;
        if (this.activeTab !== 'all') {
            items = items.filter(i => i.status === this.activeTab);
        }
        if (this.searchQuery) {
            const q = this.searchQuery.toLowerCase();
            items = items.filter(i => (i.title || i.name || '').toLowerCase().includes(q));
        }
        return items;
    },

    setTab(tab) {
        this.activeTab = tab;
    },

    itemStatusText(item) {
        const statusMap = {
            'plan_to_watch': 'Plan to Watch',
            'watching': 'Watching',
            'completed': 'Completed',
            'on_hold': 'On Hold',
            'dropped': 'Dropped'
        };
        return statusMap[item.status] || item.status;
    },

    posterUrl(path) {
        return posterUrl(path, 'w500');
    },

    async removeItem(itemId) {
        await this.$store.watchlist.removeItem(itemId);
    }
}));

// ── Content Store ────────────────────────────────────────────────────────
Alpine.store('content', {
    homeRails: [],
    genres: [],
    loading: false,

    async loadHome() {
        if (this.homeRails.length > 0) return; // already loaded
        this.loading = true;
        try {
            const data = await getHomeRails(10);
            this.homeRails = data.rails || [];
            this.genres = data.genres || [];
        } catch (e) {
            console.error('Failed to load home rails:', e);
        } finally {
            this.loading = false;
        }
    },

    async refreshHome() {
        this.homeRails = [];
        await this.loadHome();
    }
});

// ── Detail Store ─────────────────────────────────────────────────────────
Alpine.store('detail', {
    item: null,
    type: null, // 'movie' or 'series'
    loading: false,
    error: null,

    async load(type, id) {
        this.loading = true;
        this.error = null;
        this.type = type;
        try {
            this.item = type === 'series'
                ? await getSeriesDetail(id)
                : await getMovieDetail(id);
        } catch (e) {
            this.error = e.message;
            this.item = null;
        } finally {
            this.loading = false;
        }
    },

    get title() {
        if (!this.item) return '';
        return this.type === 'series' ? this.item.name : this.item.title;
    },

    get year() {
        if (!this.item) return '';
        const d = this.type === 'series' ? this.item.first_air_date : this.item.release_date;
        return d ? d.substring(0, 4) : '';
    },

    get runtime() {
        if (!this.item) return '';
        if (this.type === 'series') {
            const rt = this.item.episode_run_time;
            return rt && rt.length ? `${rt[0]}m/ep` : '';
        }
        return formatRuntime(this.item.runtime);
    },

    get genresStr() {
        return this.item ? genreString(this.item.genres) : '';
    },

    get posterSrc() {
        return this.item ? posterUrl(this.item.poster_path) : '';
    },

    get backdropSrc() {
        return this.item ? backdropUrl(this.item.backdrop_path) : '';
    },

    get overview() {
        return this.item?.overview || '';
    },

    get voteAverage() {
        return this.item?.vote_average?.toFixed(1) || '0.0';
    },

    get castList() {
        return (this.item?.cast || []).slice(0, 10);
    },

    get crewList() {
        return this.item?.crew || [];
    },

    get director() {
        const d = this.crewList.find(c => c.job === 'Director');
        return d ? d.name : '';
    },

    get seasons() {
        return this.item?.seasons || [];
    }
});

// ── Watchlist Store ──────────────────────────────────────────────────────
Alpine.store('watchlist', {
    items: [],
    loading: false,

    async load() {
        this.loading = true;
        try {
            this.items = await getWatchlist();
        } catch (e) {
            console.error('Failed to load watchlist:', e);
            this.items = [];
        } finally {
            this.loading = false;
        }
    },

    async addItem(contentType, tmdbId, status = 'plan_to_watch') {
        try {
            const item = await addToWatchlist(contentType, tmdbId, status);
            await this.load();
            Alpine.store('toast').show('Added to Watchlist!');
            return item;
        } catch (e) {
            Alpine.store('toast').show(e.message);
        }
    },

    async removeItem(itemId) {
        try {
            await removeFromWatchlist(itemId);
            await this.load();
            Alpine.store('toast').show('Removed from Watchlist.');
        } catch (e) {
            Alpine.store('toast').show(e.message);
        }
    },

    async updateItem(itemId, updates) {
        try {
            await updateWatchlistItem(itemId, updates);
            await this.load();
        } catch (e) {
            Alpine.store('toast').show(e.message);
        }
    },

    isBookmarked(tmdbId) {
        return this.items.some(i => i.tmdb_id === tmdbId);
    },

    getItemByTmdbId(tmdbId) {
        return this.items.find(i => i.tmdb_id === tmdbId);
    }
});

// ── Profile Store ────────────────────────────────────────────────────────
Alpine.store('profile', {
    stats: null,
    loading: false,

    async loadStats() {
        this.loading = true;
        try {
            this.stats = await getProfileStats();
        } catch (e) {
            console.error('Failed to load profile stats:', e);
        } finally {
            this.loading = false;
        }
    }
});

// Start Alpine
Alpine.start();

// --- DOM Ready ---
document.addEventListener('DOMContentLoaded', async () => {
    await pages_ready;
    switchPage('login');
    initSearch();
    initFilters();

    // ── Helper: load data when switching pages ───────────────────────────
    async function onNavigate(pageId) {
        switchPage(pageId);
        if (pageId === 'discover') {
            Alpine.store('content').loadHome();
        } else if (pageId === 'watchlists') {
            Alpine.store('watchlist').load();
            Alpine.store('profile').loadStats();
        } else if (pageId === 'movies') {
            Alpine.store('content').loadHome();
        }
    }

    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const targetPage = link.getAttribute('data-page');
            if (targetPage) onNavigate(targetPage);
        });
    });

    document.addEventListener('click', (e) => {
        // 1. Movie/Series Card Click -> Go to Detail
        const movieCard = e.target.closest('.movie-card');
        if (movieCard && !e.target.closest('.bookmark-btn') && !e.target.closest('.episode-card')) {
            const tmdbId = movieCard.dataset.tmdbId;
            const contentType = movieCard.dataset.contentType;
            if (tmdbId && contentType) {
                Alpine.store('detail').load(contentType, parseInt(tmdbId));
                switchPage('detail');
            } else {
                switchPage('detail');
            }
            return;
        }

        // 2. Watch Now Button or Episode Card -> Go to Watching
        const epCard = e.target.closest('.episode-card');
        const watchBtn = e.target.closest('#btn-watch-now') || e.target.closest('.hero .btn-primary') || epCard;
        if (watchBtn) {
            if (epCard) {
                const epTitle = epCard.querySelector('h3')?.innerText || '';
                const epDesc = epCard.querySelector('p')?.innerText || '';
                const playerTitle = document.querySelector('.player-title');
                const playerDesc = document.querySelector('#page-watching .detail-desc');
                if (playerTitle) playerTitle.innerText = epTitle;
                if (playerDesc) playerDesc.innerText = epDesc;
            }
            switchPage('watching');
            return;
        }

        // 3. Login Button -> handled by Alpine x-data="loginForm"
        // 4. Avatar Dropdown -> handled by Alpine x-data="dropdown"

        // 5. Logout Button -> Go to Login
        const logoutBtn = e.target.closest('#logout-btn');
        if (logoutBtn) {
            Alpine.store('auth').logout();
            switchPage('login');
            return;
        }

        // 6. Mobile Menu Toggle
        const mobileMenuBtn = e.target.closest('#mobile-menu-btn');
        if (mobileMenuBtn) {
            const navLinksContainer = document.querySelector('.nav-links');
            if (navLinksContainer) navLinksContainer.classList.toggle('active');
        }

        // 7. Bookmarking Logic → API-backed
        const bookmarkBtn = e.target.closest('.bookmark-btn');
        if (bookmarkBtn) {
            const card = bookmarkBtn.closest('.movie-card');
            const tmdbId = card?.dataset.tmdbId;
            const contentType = card?.dataset.contentType || 'movie';

            if (tmdbId) {
                const existing = Alpine.store('watchlist').getItemByTmdbId(parseInt(tmdbId));
                if (existing) {
                    Alpine.store('watchlist').removeItem(existing._id);
                } else {
                    Alpine.store('watchlist').addItem(contentType, parseInt(tmdbId));
                }
            } else {
                // Fallback for static cards without data attributes
                bookmarkBtn.classList.toggle('active');
                const icon = bookmarkBtn.querySelector('svg');
                if (bookmarkBtn.classList.contains('active')) {
                    bookmarkBtn.style.background = 'var(--accent-gold)';
                    if (icon) icon.style.fill = 'black';
                    Alpine.store('toast').show("Added to Watchlist!");
                } else {
                    bookmarkBtn.style.background = 'rgba(122, 120, 128, 0.5)';
                    if (icon) icon.style.fill = 'none';
                    Alpine.store('toast').show("Removed from Watchlist.");
                }
            }
        }

        // 8. Generic Tab/Chip Switching
        const chip = e.target.closest('.filter-chip');
        if (chip) {
            chip.parentElement.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('active'));
            chip.classList.add('active');
        }

        const tab = e.target.closest('.list-tab, .season-tab');
        if (tab) {
            tab.parentElement.querySelectorAll('.list-tab, .season-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            const tabName = tab.innerText.toLowerCase();
            const watchlistGrid = document.querySelector('.watchlist-grid');
            if (tab.classList.contains('list-tab') && watchlistGrid) {
                const cards = watchlistGrid.querySelectorAll('.movie-card');
                cards.forEach(card => {
                    const status = card.querySelector('.card-status')?.innerText.toLowerCase() || card.dataset.status;
                    card.style.display = (tabName === 'all' || (status && status.includes(tabName))) ? 'block' : 'none';
                });
            }
        }

        // 9. "Start Watching" hero CTA -> navigate to discover
        const startBtn = e.target.closest('#btn-watch-now');
        if (startBtn && startBtn.closest('.nf-hero')) {
            onNavigate('discover');
            return;
        }

        // 10. "Back to Discover" / "Go to Discover" links
        const discoverLink = e.target.closest('a[href="#discover"]');
        if (discoverLink) {
            e.preventDefault();
            onNavigate('discover');
            return;
        }

        // 11. "Back to details" link
        const detailLink = e.target.closest('a[href="#detail"]');
        if (detailLink) {
            e.preventDefault();
            switchPage('detail');
            return;
        }

        // 12. "Open Watchlists" / "Browse more titles" links
        const watchlistLink = e.target.closest('a[href="#watchlists"]');
        if (watchlistLink) {
            e.preventDefault();
            onNavigate('watchlists');
            return;
        }

        // 13. "Browse full chart" / Movies link
        const moviesLink = e.target.closest('a[href="#movies"]');
        if (moviesLink) {
            e.preventDefault();
            onNavigate('movies');
            return;
        }

        // 14. "Original series" / Series link
        const seriesLink = e.target.closest('a[href="#series"]');
        if (seriesLink) {
            e.preventDefault();
            onNavigate('series');
            return;
        }
    });
});
