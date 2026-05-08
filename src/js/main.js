import Alpine from 'alpinejs';
import { pages_ready } from './pages.js';
import { switchPage } from './router.js';
import { contentApi, watchlistApi, historyApi, adminApi, ratingsApi, apiFetch } from './api.js';
import { initPreloader } from './preloader.js';
import {
    animateHeroContent,
    initHeroParallax,
    staggerCards,
    animateRanks,
    animateDetailHero,
    animateCast,
    animatePlayerEntry,
    initScrollReveals,
    animateCounter,
    prefersReducedMotion,
    showPageLoader,
} from './animations.js';

window.Alpine = Alpine;
window.switchPage = switchPage;
window.vozAnimations = {
    animateHeroContent,
    initHeroParallax,
    staggerCards,
    animateRanks,
    animateDetailHero,
    animateCast,
    animatePlayerEntry,
    initScrollReveals,
    animateCounter,
    prefersReducedMotion,
    showPageLoader,
};

// --- Netflix-style navbar scroll effect ---
window.addEventListener('scroll', () => {
    const nav = document.getElementById('main-nav');
    if (nav) {
        if (window.scrollY > 30) {
            nav.classList.add('scrolled');
        } else {
            nav.classList.remove('scrolled');
        }
    }
}, { passive: true });

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
        let data;
        try { data = await res.json(); } catch { throw new Error('Server is unreachable. Please try again later.'); }
        if (!res.ok) throw new Error(data.error || data.detail);
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
        let data;
        try { data = await res.json(); } catch { throw new Error('Server is unreachable. Please try again later.'); }
        if (!res.ok) throw new Error(data.error || data.detail);
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
                try { this.user = await res.json(); } catch { /* non-JSON response */ }
            } else {
                this.logout();
            }
        } catch { this.logout(); }
    }
});

Alpine.store('nav', {
    currentPage: 'login',
    contentId: null,
    contentType: null,
});

// --- Alpine Components ---
Alpine.data('appState', () => ({
    init() {
        // Fire-and-forget: fetchUser stores the result in the store.
        // The actual initial page switch is handled in DOMContentLoaded
        // to avoid a race condition that overrides user navigation.
        Alpine.store('auth').fetchUser();
    }
}));

/* ---- Scroll Rail Component (horizontal content rows with arrow nav) ---- */
Alpine.data('scrollRail', () => ({
    canScrollLeft: false,
    canScrollRight: false,
    _resizeObs: null,

    init() {
        this.$nextTick(() => {
            this.checkArrows();
            const el = this.$refs.scrollContainer;
            if (el && typeof ResizeObserver !== 'undefined') {
                this._resizeObs = new ResizeObserver(() => this.checkArrows());
                this._resizeObs.observe(el);
            }
        });
    },

    destroy() {
        if (this._resizeObs) {
            this._resizeObs.disconnect();
            this._resizeObs = null;
        }
    },

    checkArrows() {
        const el = this.$refs.scrollContainer;
        if (!el) return;
        this.canScrollLeft = el.scrollLeft > 4;
        this.canScrollRight = el.scrollLeft < el.scrollWidth - el.clientWidth - 4;
    },

    scrollLeft() {
        const el = this.$refs.scrollContainer;
        if (!el) return;
        el.scrollBy({ left: -el.clientWidth * 0.75, behavior: 'smooth' });
    },

    scrollRight() {
        const el = this.$refs.scrollContainer;
        if (!el) return;
        el.scrollBy({ left: el.clientWidth * 0.75, behavior: 'smooth' });
    },
}));

Alpine.data('discoverPage', () => ({
    rails: [],
    loading: false,
    error: '',
    carouselIndex: 0,
    carouselPaused: false,
    _carouselTimer: null,

    init() {
        document.addEventListener('page:switch', (e) => {
            if (e.detail.pageId === 'discover') this.loadHome();
        });
        this.loadHome();
    },

    async loadHome() {
        if (this.rails.length > 0) return;
        this.loading = true;
        this.error = '';
        try {
            const data = await contentApi.getHome();
            this.rails = (data.rails || []).filter(r => r.items && r.items.length > 0 && r.id !== 'continue_watching');
        } catch (e) {
            this.error = e.message;
        } finally {
            this.loading = false;
            this.$nextTick(() => this._startCarousel());
        }
    },

    /* ---- Hero Carousel ---- */
    get heroSlides() {
        const rail = this.top10Rail;
        if (!rail) return [];
        return rail.items.slice(0, 6).map(item => ({
            ...item,
            _type: rail.content_type,
            backdropUrl: item.backdrop_path
                ? `https://image.tmdb.org/t/p/original${item.backdrop_path}`
                : item.poster_path
                    ? `https://image.tmdb.org/t/p/original${item.poster_path}`
                    : '',
            posterUrl: item.poster_path
                ? `https://image.tmdb.org/t/p/w500${item.poster_path}`
                : 'https://placehold.co/300x450/1a1a2e/white?text=No+Image',
            title: rail.content_type === 'series' ? (item.name || item.title) : (item.title || item.name),
            year: (() => {
                const d = rail.content_type === 'series' ? item.first_air_date : item.release_date;
                return d ? d.substring(0, 4) : '';
            })(),
        }));
    },

    get currentSlide() {
        return this.heroSlides[this.carouselIndex] || null;
    },

    carouselNext() {
        if (this.heroSlides.length === 0) return;
        this.carouselIndex = (this.carouselIndex + 1) % this.heroSlides.length;
    },

    carouselPrev() {
        if (this.heroSlides.length === 0) return;
        this.carouselIndex = (this.carouselIndex - 1 + this.heroSlides.length) % this.heroSlides.length;
    },

    carouselGo(i) {
        this.carouselIndex = i;
    },

    carouselPause() {
        this.carouselPaused = true;
        this._stopCarousel();
    },

    carouselResume() {
        this.carouselPaused = false;
        this._startCarousel();
    },

    _startCarousel() {
        this._stopCarousel();
        if (this.heroSlides.length <= 1) return;
        this._carouselTimer = setInterval(() => {
            if (!this.carouselPaused) this.carouselNext();
        }, 6000);
    },

    _stopCarousel() {
        if (this._carouselTimer) {
            clearInterval(this._carouselTimer);
            this._carouselTimer = null;
        }
    },

    /* ---- Content Rails ---- */
    get top10Rail() {
        return this.rails.find(r => r.items && r.items.length >= 5) || this.rails[0] || null;
    },
    get top10() {
        return (this.top10Rail?.items || []).slice(0, 9);
    },
    get top10ContentType() {
        return this.top10Rail?.content_type || 'movie';
    },
    get otherRails() {
        const top = this.top10Rail;
        return this.rails.filter(r => r !== top).slice(0, 3);
    },

    navigateTo(item, contentType) {
        switchPage('detail', { contentId: item.tmdb_id, contentType: contentType || 'movie' });
    },

    posterUrl(path) {
        return path ? `https://image.tmdb.org/t/p/w500${path}` : 'https://placehold.co/300x450/1a1a2e/white?text=No+Image';
    },

    getTitle(item, ct) {
        return ct === 'series' ? (item.name || item.title) : (item.title || item.name);
    },

    getYear(item, ct) {
        const d = ct === 'series' ? item.first_air_date : item.release_date;
        return d ? d.substring(0, 4) : '';
    },
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

Alpine.data('navSearch', () => ({
    query: '',
    results: [],
    loading: false,
    open: false,
    _debounceTimer: null,
    _lastQuery: '',
    _searchSeq: 0,

    onInput() {
        clearTimeout(this._debounceTimer);
        const trimmed = this.query.trim();
        if (trimmed.length < 2) {
            this.results = [];
            this.loading = false;
            this._lastQuery = '';
            this.open = false;
            return;
        }
        this.open = true;
        this.loading = true;
        this._debounceTimer = setTimeout(() => this._runSearch(trimmed), 150);
    },

    async _runSearch(q) {
        if (q === this._lastQuery) {
            this.loading = false;
            return;
        }
        this._lastQuery = q;
        const seq = ++this._searchSeq;
        try {
            const data = await contentApi.search(q, 1, 8);
            if (seq !== this._searchSeq) return;
            this.results = (data.results || []).slice(0, 8);
        } catch (e) {
            if (seq !== this._searchSeq) return;
            this.results = [];
            Alpine.store('toast').show('Search failed: ' + e.message);
        } finally {
            if (seq === this._searchSeq) this.loading = false;
        }
    },

    submit() {
        const trimmed = this.query.trim();
        if (!trimmed) return;
        switchPage('movies', { searchQuery: trimmed });
        document.dispatchEvent(new CustomEvent('nav:search', { detail: { query: trimmed } }));
        this.close();
    },

    goToResult(item) {
        switchPage('detail', {
            contentId: item.tmdb_id,
            contentType: item.content_type || 'movie',
        });
        this.close();
    },

    close() {
        this.open = false;
    },

    getTitle(item) {
        return item.content_type === 'series'
            ? (item.name || item.title)
            : (item.title || item.name);
    },

    getYear(item) {
        const d = item.content_type === 'series' ? item.first_air_date : item.release_date;
        return d ? d.substring(0, 4) : '';
    },

    posterUrl(path) {
        return path
            ? `https://image.tmdb.org/t/p/w92${path}`
            : 'https://placehold.co/46x69/1a1a2e/white?text=%3F';
    },
}));

Alpine.data('filterPanel', () => ({
    open: false,
    toggle() { this.open = !this.open; }
}));

Alpine.data('faqItem', () => ({
    open: false,
    toggle() { this.open = !this.open; }
}));

Alpine.data('moviesPage', () => ({
    rails: [],
    genres: [],
    loading: false,
    error: '',
    searchQuery: '',
    searchResults: [],
    searching: false,
    isSearchMode: false,
    _lastQuery: '',
    browsingGenre: null,
    browseResults: [],
    browseLoading: false,
    browsePage: 1,
    _debounceTimer: null,

    async init() {
        document.addEventListener('page:switch', (e) => {
            if (e.detail.pageId === 'movies') {
                const q = e.detail.params?.searchQuery;
                if (q) {
                    this.searchQuery = q;
                    this.runSearch(q);
                } else if (this.rails.length === 0) {
                    this.loadHome();
                }
            }
        });
        document.addEventListener('nav:search', (e) => {
            this.searchQuery = e.detail.query;
            this.runSearch(e.detail.query);
        });
        this.loadHome();
    },

    async loadHome() {
        if (this.rails.length > 0) return;
        this.loading = true;
        this.error = '';
        try {
            const [homeData, genresData] = await Promise.all([
                contentApi.getHome(),
                contentApi.getGenres(),
            ]);
            this.rails = (homeData.rails || []).filter(r => r.items && r.items.length > 0);
            this.genres = genresData || [];
        } catch (e) {
            this.error = e.message;
        } finally {
            this.loading = false;
        }
    },

    onSearchInput(value) {
        this.searchQuery = value;
        clearTimeout(this._debounceTimer);
        const trimmed = value.trim();
        if (trimmed.length < 2) {
            this.isSearchMode = false;
            this.searchResults = [];
            this._lastQuery = '';
            return;
        }
        this._debounceTimer = setTimeout(() => this.runSearch(trimmed), 400);
    },

    async runSearch(q) {
        if (q === this._lastQuery && this.isSearchMode) return;
        this._lastQuery = q;
        this.searching = true;
        this.isSearchMode = true;
        this.browsingGenre = null;
        try {
            const data = await contentApi.search(q);
            this.searchResults = data.results || data.movies || data || [];
        } catch (e) {
            Alpine.store('toast').show('Search failed: ' + e.message);
        } finally {
            this.searching = false;
        }
    },

    async browseGenre(genreId, genreName) {
        this.browsingGenre = { id: genreId, name: genreName };
        this.isSearchMode = false;
        this.browseLoading = true;
        this.browsePage = 1;
        try {
            const data = await contentApi.browse(genreId, 1, 20);
            const movies = (data.movies || []).map(m => ({ ...m, _ct: 'movie' }));
            const series = (data.series || []).map(s => ({ ...s, _ct: 'series' }));
            this.browseResults = [...movies, ...series];
        } catch (e) {
            Alpine.store('toast').show('Browse failed: ' + e.message);
        } finally {
            this.browseLoading = false;
        }
    },

    clearBrowse() {
        this.browsingGenre = null;
        this.isSearchMode = false;
        this.searchQuery = '';
        this.searchResults = [];
        this._lastQuery = '';
    },

    navigateTo(item, contentType) {
        switchPage('detail', { contentId: item.tmdb_id, contentType });
    },

    posterUrl(path) {
        return path ? `https://image.tmdb.org/t/p/w500${path}` : 'https://placehold.co/300x450/1a1a2e/white?text=No+Image';
    },

    getTitle(item, contentType) {
        return contentType === 'series' ? (item.name || item.title) : (item.title || item.name);
    },

    getYear(item, contentType) {
        const d = contentType === 'series' ? item.first_air_date : item.release_date;
        return d ? d.substring(0, 4) : '';
    },
}));

Alpine.data('seriesPage', () => ({
    rails: [],
    loading: false,
    error: '',

    async init() {
        document.addEventListener('page:switch', (e) => {
            if (e.detail.pageId === 'series') this.loadSeries();
        });
        this.loadSeries();
    },

    async loadSeries() {
        if (this.rails.length > 0) return;
        this.loading = true;
        this.error = '';
        try {
            const data = await contentApi.getHome();
            this.rails = (data.rails || []).filter(r => r.content_type === 'series' && r.items && r.items.length > 0);
        } catch (e) {
            this.error = e.message;
        } finally {
            this.loading = false;
        }
    },

    navigateTo(item) {
        switchPage('detail', { contentId: item.tmdb_id, contentType: 'series' });
    },

    posterUrl(path) {
        return path ? `https://image.tmdb.org/t/p/w500${path}` : 'https://placehold.co/300x450/1a1a2e/white?text=No+Image';
    },
}));

Alpine.data('detailPage', () => ({
    content: null,
    contentType: null,
    loading: false,
    error: '',
    watchlistItem: null,
    selectedSeason: 0,

    // Rating & Review state
    ratings: [],
    stats: { average: 0, count: 0, distribution: {} },
    myRating: null,
    userRating: 0,
    userReview: '',
    submitting: false,
    showReviewForm: false,
    reviewsPage: 1,
    hasMoreReviews: false,
    activeTab: 'overview',  // 'overview' | 'reviews'

    init() {
        document.addEventListener('page:switch', (e) => {
            if (e.detail.pageId === 'detail') {
                this.load(e.detail.params.contentId, e.detail.params.contentType);
            }
        });
    },

    async load(contentId, contentType) {
        if (!contentId) return;
        this.loading = true;
        this.content = null;
        this.error = '';
        this.contentType = contentType;
        this.selectedSeason = 0;
        this.activeTab = 'overview';
        this.userRating = 0;
        this.userReview = '';
        this.myRating = null;

        // Show branded page preloader
        const loaderContainer = document.getElementById('detail-loader');
        const va = window.vozAnimations;
        let pageLoader = null;
        if (loaderContainer && va) {
            loaderContainer.innerHTML = '';
            pageLoader = va.showPageLoader(loaderContainer, 'Loading details…');
        }

        try {
            if (contentType === 'series') {
                this.content = await contentApi.getSeries(contentId);
            } else {
                try {
                    this.content = await contentApi.getMovie(contentId);
                } catch (movieErr) {
                    // If movie fetch fails (e.g. 404 — stale content_type in history),
                    // retry as series. This handles entries incorrectly stored as "movie".
                    if (String(movieErr.message).includes('404')) {
                        this.contentType = 'series';
                        this.content = await contentApi.getSeries(contentId);
                    } else {
                        throw movieErr;
                    }
                }
            }
            await this.checkWatchlistStatus(contentId, contentType);
            await this.loadRatings(contentId, contentType);
        } catch (e) {
            this.error = 'Failed to load: ' + e.message;
        } finally {
            // Hide the branded preloader, then reveal content
            if (pageLoader) {
                await pageLoader.hide();
            }
            this.loading = false;
            // Trigger detail hero animation
            this.$nextTick(() => {
                if (va) {
                    const container = document.getElementById('page-detail');
                    if (container) {
                        va.animateDetailHero(container);
                        va.initScrollReveals(container);
                    }
                }
            });
        }
    },

    async loadRatings(contentId, contentType) {
        try {
            const data = await ratingsApi.get(contentId, contentType, false, 1, 50);
            this.ratings = data.ratings || [];
            this.stats = data.stats || { average: 0, count: 0, distribution: {} };
            this.hasMoreReviews = this.ratings.length >= 50;
            this.reviewsPage = 1;
        } catch { /* silent */ }

        // Load user's own rating
        if (Alpine.store('auth').isLoggedIn) {
            try {
                const mine = await ratingsApi.getMine(contentType);
                const found = mine.find(r => r.tmdb_id === contentId && r.content_type === contentType);
                if (found) {
                    this.myRating = found;
                    this.userRating = found.rating;
                    this.userReview = found.review || '';
                } else {
                    this.myRating = null;
                    this.userRating = 0;
                    this.userReview = '';
                }
            } catch { /* silent */ }
        }
    },

    async loadMoreReviews() {
        this.reviewsPage++;
        try {
            const data = await ratingsApi.get(
                Alpine.store('nav').contentId,
                this.contentType, false, this.reviewsPage, 50
            );
            const newRatings = data.ratings || [];
            this.ratings = [...this.ratings, ...newRatings];
            this.hasMoreReviews = newRatings.length >= 50;
        } catch { /* silent */ }
    },

    async submitRating() {
        if (!Alpine.store('auth').isLoggedIn) { switchPage('login'); return; }
        if (this.userRating < 1) {
            Alpine.store('toast').show('Please select a rating first.');
            return;
        }
        this.submitting = true;
        try {
            const contentId = Alpine.store('nav').contentId;
            await ratingsApi.create(
                this.contentType, contentId,
                this.userRating,
                this.userReview.trim() || null
            );
            Alpine.store('toast').show('Rating saved!');
            await this.loadRatings(contentId, this.contentType);
            this.showReviewForm = false;
        } catch (e) {
            Alpine.store('toast').show('Error: ' + e.message);
        } finally {
            this.submitting = false;
        }
    },

    async deleteMyRating() {
        if (!this.myRating) return;
        try {
            const contentId = Alpine.store('nav').contentId;
            await ratingsApi.remove(this.contentType, contentId);
            this.myRating = null;
            this.userRating = 0;
            this.userReview = '';
            Alpine.store('toast').show('Rating removed.');
            await this.loadRatings(contentId, this.contentType);
        } catch (e) {
            Alpine.store('toast').show('Error: ' + e.message);
        }
    },

    setUserRating(n) {
        this.userRating = this.userRating === n ? 0 : n;
    },

    get reviewList() {
        return this.ratings.filter(r => r.review && r.review.trim().length > 0);
    },

    get displayRatings() {
        return this.ratings;
    },

    get averageDisplay() {
        return this.stats.average ? this.stats.average.toFixed(1) : '—';
    },

    get maxDistribution() {
        const d = this.stats.distribution || {};
        return Math.max(1, ...Object.values(d));
    },

    formatDate(dateStr) {
        if (!dateStr) return '';
        try {
            return new Date(dateStr).toLocaleDateString('en-US', {
                year: 'numeric', month: 'short', day: 'numeric'
            });
        } catch { return ''; }
    },

    getInitial(name) {
        return (name || '?').charAt(0).toUpperCase();
    },

    async checkWatchlistStatus(contentId, contentType) {
        if (!Alpine.store('auth').isLoggedIn) { this.watchlistItem = null; return; }
        try {
            const items = await watchlistApi.getAll();
            this.watchlistItem = items.find(i => i.tmdb_id === contentId && i.content_type === contentType) || null;
        } catch { this.watchlistItem = null; }
    },

    get title() { return this.contentType === 'series' ? this.content?.name : this.content?.title; },
    get year() {
        const d = this.contentType === 'series' ? this.content?.first_air_date : this.content?.release_date;
        return d ? d.substring(0, 4) : '';
    },
    get backdropUrl() {
        return this.content?.backdrop_path
            ? `https://image.tmdb.org/t/p/original${this.content.backdrop_path}`
            : 'https://placehold.co/1280x720/1a1a2e/white?text=No+Backdrop';
    },
    get posterUrl() {
        return this.content?.poster_path
            ? `https://image.tmdb.org/t/p/w500${this.content.poster_path}`
            : 'https://placehold.co/300x450/1a1a2e/white?text=No+Image';
    },
    get castString() { return (this.content?.cast || []).slice(0, 5).map(c => c.name).join(' · ') || '—'; },
    get genreString() { return (this.content?.genres || []).map(g => g.name).join(', ') || '—'; },
    get runtime() {
        if (this.contentType === 'series') {
            const n = this.content?.number_of_seasons;
            return n ? `${n} season${n > 1 ? 's' : ''}` : '';
        }
        const m = this.content?.runtime;
        return m ? `${Math.floor(m / 60)}h ${m % 60}m` : '';
    },
    get currentSeasonEpisodes() {
        if (!this.content?.seasons) return [];
        return this.content.seasons[this.selectedSeason]?.episodes || [];
    },

    async toggleBookmark() {
        if (!Alpine.store('auth').isLoggedIn) { switchPage('login'); return; }
        const contentId = Alpine.store('nav').contentId;
        const contentType = Alpine.store('nav').contentType;
        try {
            if (this.watchlistItem) {
                await watchlistApi.remove(this.watchlistItem._id);
                this.watchlistItem = null;
                Alpine.store('toast').show('Removed from Watchlist.');
            } else {
                const item = await watchlistApi.add(contentType, contentId, 'plan_to_watch');
                this.watchlistItem = item;
                Alpine.store('toast').show('Added to Watchlist!');
            }
        } catch (e) {
            Alpine.store('toast').show('Error: ' + e.message);
        }
    },

    async toggleCompleted() {
        if (!Alpine.store('auth').isLoggedIn) { switchPage('login'); return; }
        const contentId = Alpine.store('nav').contentId;
        const contentType = Alpine.store('nav').contentType;
        try {
            if (this.watchlistItem) {
                const nextStatus = this.watchlistItem.status === 'completed' ? 'plan_to_watch' : 'completed';
                const updated = await watchlistApi.update(this.watchlistItem._id, { status: nextStatus });
                this.watchlistItem = updated;
                Alpine.store('toast').show(nextStatus === 'completed' ? 'Marked as watched.' : 'Moved back to Watchlist.');
            } else {
                const item = await watchlistApi.add(contentType, contentId, 'completed');
                this.watchlistItem = item;
                Alpine.store('toast').show('Marked as watched.');
            }
        } catch (e) {
            Alpine.store('toast').show('Error: ' + e.message);
        }
    },

    async toggleFavorite() {
        if (!Alpine.store('auth').isLoggedIn) { switchPage('login'); return; }
        const contentId = Alpine.store('nav').contentId;
        const contentType = Alpine.store('nav').contentType;
        try {
            if (this.watchlistItem) {
                const next = !this.watchlistItem.is_favorite;
                const updated = await watchlistApi.update(this.watchlistItem._id, { is_favorite: next });
                this.watchlistItem = updated;
                Alpine.store('toast').show(next ? 'Added to Favorites!' : 'Removed from Favorites.');
            } else {
                const item = await watchlistApi.add(contentType, contentId, 'plan_to_watch', { is_favorite: true });
                this.watchlistItem = item;
                Alpine.store('toast').show('Added to Favorites!');
            }
        } catch (e) {
            Alpine.store('toast').show('Error: ' + e.message);
        }
    },
}));

Alpine.data('watchingPage', () => ({
    content: null,
    contentType: null,
    loading: false,
    error: '',
    selectedEpisode: null,
    selectedSeasonIndex: 0,
    _lastPostAt: 0,
    _lastMessageAt: 0,
    _everReceivedMsg: false,
    _fallbackPollId: null,
    activeProvider: 'vidlink',

    providers: {
        vidlink: {
            name: 'Server #1',
            movie: (id) => `https://vidlink.pro/movie/${id}?primaryColor=f4c84a&autoplay=true&title=true&poster=true`,
            tv: (id, s, e) => `https://vidlink.pro/tv/${id}/${s}/${e}?primaryColor=f4c84a&autoplay=true&nextbutton=true&title=true&poster=true`,
        },
        '2embed': {
            name: 'Server #2',
            movie: (id) => `https://www.2embed.cc/embed/${id}`,
            tv: (id, s, e) => `https://www.2embed.cc/embedtv/${id}&s=${s}&e=${e}`,
        },
        vidking: {
            name: 'Server #3',
            movie: (id) => `https://www.vidking.net/embed/movie/${id}?color=f4c84a&autoPlay=true`,
            tv: (id, s, e) => `https://www.vidking.net/embed/tv/${id}/${s}/${e}?color=f4c84a&autoPlay=true&nextEpisode=true&episodeSelector=true`,
        },
    },

    init() {
        document.addEventListener('page:switch', (e) => {
            if (e.detail.pageId !== 'watching') return;
            const params = e.detail.params || {};
            const contentId = params.contentId || Alpine.store('nav').contentId;
            const contentType = params.contentType || Alpine.store('nav').contentType || 'movie';
            this.load(contentId, contentType);
        });

        // Embed player → parent postMessage bridge.
        // One listener for the lifetime of the SPA; handler ignores events
        // when the iframe isn't loaded or the user is anonymous.
        window.addEventListener('message', (event) => this._onPlayerMessage(event));
    },

    async load(contentId, contentType) {
        if (!contentId) {
            this.error = 'No content selected.';
            return;
        }
        this.loading = true;
        this.error = '';
        this.contentType = contentType;
        this.selectedEpisode = null;
        this.selectedSeasonIndex = 0;
        this._lastPostAt = 0;
        this._lastMessageAt = 0;
        this._everReceivedMsg = false;
        this._stopFallbackPoll();
        try {
            try {
                this.content = contentType === 'series'
                    ? await contentApi.getSeries(contentId)
                    : await contentApi.getMovie(contentId);
            } catch (fetchErr) {
                // If 404, retry with the other content type (stale content_type in history)
                if (String(fetchErr.message).includes('404')) {
                    this.contentType = contentType === 'series' ? 'movie' : 'series';
                    this.content = this.contentType === 'series'
                        ? await contentApi.getSeries(contentId)
                        : await contentApi.getMovie(contentId);
                } else {
                    throw fetchErr;
                }
            }
            if (this.contentType === 'series') {
                const eps = this.content?.seasons?.[0]?.episodes || [];
                this.selectedEpisode = eps[0] || null;
            }
        } catch (e) {
            this.error = 'Failed to load: ' + e.message;
        } finally {
            this.loading = false;
            // Reset click shield when new content/episode loads
            window.dispatchEvent(new Event('content-loaded'));
            // Start fallback poll for providers that don't send postMessage
            this._startFallbackPoll();
            // Trigger player entry animation
            this.$nextTick(() => {
                const va = window.vozAnimations;
                if (va) {
                    const container = document.getElementById('page-watching');
                    if (container) va.animatePlayerEntry(container);
                }
            });
        }
    },

    get playerSrc() {
        if (!this.content?.tmdb_id) return '';
        const id = this.content.tmdb_id;
        const provider = this.providers[this.activeProvider];
        if (this.contentType === 'series') {
            const season = this.selectedEpisode
                ? (this.content?.seasons?.[this.selectedSeasonIndex]?.season_number ?? 1)
                : 1;
            const ep = this.selectedEpisode?.episode_number ?? 1;
            return provider.tv(id, season, ep);
        }
        return provider.movie(id);
    },

    switchProvider(key) {
        if (this.activeProvider === key) return;
        this.activeProvider = key;
        this._lastPostAt = 0;
        this._lastMessageAt = 0;
        this._everReceivedMsg = false;
        this._stopFallbackPoll();
        window.dispatchEvent(new Event('content-loaded'));
        this._startFallbackPoll();
    },

    selectEpisode(ep) {
        this.selectedEpisode = ep;
        this._lastPostAt = 0;
        this._lastMessageAt = 0;
        this._everReceivedMsg = false;
        this._stopFallbackPoll();
        // Reset click shield for new episode
        window.dispatchEvent(new Event('content-loaded'));
        this._startFallbackPoll();
        // playerSrc getter recomputes; Alpine re-binds :src and the iframe reloads.
    },

    get title() {
        if (!this.content) return '';
        const base = this.contentType === 'series' ? (this.content.name || this.content.title) : (this.content.title || this.content.name);
        if (this.selectedEpisode) {
            const epLabel = this.selectedEpisode.name || `Episode ${this.selectedEpisode.episode_number}`;
            return `${base} · ${epLabel}`;
        }
        return base || '';
    },
    get description() {
        return this.selectedEpisode?.overview || this.content?.overview || '';
    },
    get rating() {
        return (this.content?.vote_average ?? 0).toFixed(1);
    },
    get metaLine() {
        if (!this.content) return '';
        if (this.contentType === 'series') {
            const season = this.content?.seasons?.[this.selectedSeasonIndex];
            return season ? `Season ${season.season_number}` : '';
        }
        const m = this.content?.runtime;
        return m ? `${Math.floor(m / 60)}h ${m % 60}m` : '';
    },
    get backdropUrl() {
        return this.content?.backdrop_path
            ? `https://image.tmdb.org/t/p/original${this.content.backdrop_path}`
            : '';
    },
    get upNext() {
        if (this.contentType !== 'series' || !this.selectedEpisode) return [];
        const eps = this.content?.seasons?.[this.selectedSeasonIndex]?.episodes || [];
        return eps;
    },

    episodeThumb(ep) {
        if (ep?.still_path) return `https://image.tmdb.org/t/p/w500${ep.still_path}`;
        if (this.content?.backdrop_path) return `https://image.tmdb.org/t/p/w500${this.content.backdrop_path}`;
        return 'https://placehold.co/500x281/1a1a2e/white?text=Episode';
    },

    // ─── Fallback progress polling ───────────────────────────────
    // For providers (e.g. 2embed) that don't send postMessage events.
    // If no message is received within 20s of starting playback,
    // poll every 15s and post a best-effort progress estimate.

    _startFallbackPoll() {
        this._stopFallbackPoll();
        // Give the provider 20s to send at least one message
        this._fallbackPollId = setTimeout(() => {
            // If we already received a message from the provider, no need to poll
            if (this._everReceivedMsg) return;

            // Start periodic polling
            this._fallbackPollId = setInterval(() => {
                if (!Alpine.store('auth').isLoggedIn || !this.content?.tmdb_id) return;
                // Only poll if the document is visible (user is actually watching)
                if (document.visibilityState !== 'visible') return;
                // If the provider started sending messages, stop polling
                if (this._everReceivedMsg) {
                    this._stopFallbackPoll();
                    return;
                }

                // Post a keep-alive so the entry stays in "Continue Watching".
                // Use progress_seconds: 1 (not 0) because the backend filters
                // for progress_seconds > 0. The backend $set will only update
                // last_watched_at — it won't clobber a higher progress value
                // because we never decrease it here.
                historyApi.postProgress({
                    content_type: this.contentType,
                    tmdb_id: this.content.tmdb_id,
                    progress_seconds: 1,
                    completed: false,
                    season_number: this.selectedEpisode
                        ? (this.content?.seasons?.[this.selectedSeasonIndex]?.season_number ?? null)
                        : null,
                    episode_number: this.selectedEpisode?.episode_number ?? null,
                }).catch(() => {});
            }, 15000);
        }, 20000);
    },

    _stopFallbackPoll() {
        if (this._fallbackPollId) {
            clearTimeout(this._fallbackPollId);
            clearInterval(this._fallbackPollId);
            this._fallbackPollId = null;
        }
    },

    _onPlayerMessage(event) {
        if (!Alpine.store('auth').isLoggedIn || !this.content?.tmdb_id) return;

        // --- Normalize message data ---
        // VidLink sends structured objects: { type: 'PLAYER_EVENT', data: {...} }
        // VidKing may send a JSON string that needs parsing.
        let msg = event.data;
        if (typeof msg === 'string') {
            try { msg = JSON.parse(msg); } catch { return; }
        }
        if (!msg || typeof msg !== 'object') return;

        // --- Extract payload from different provider formats ---
        let payload = null;
        let eventType = null;
        let currentTime = null;

        // Format 1: { type: 'PLAYER_EVENT', data: { event, currentTime, ... } }
        // Used by VidLink and VidKing (when sending structured objects)
        if (msg.type === 'PLAYER_EVENT' && msg.data) {
            payload = msg.data;
            eventType = payload.event;
            currentTime = payload.currentTime;
        }
        // Format 2: { type: 'MEDIA_DATA', data: { id, type, progress: { watched, duration }, ... } }
        // VidLink sends this on pause/seek/end with detailed progress
        else if (msg.type === 'MEDIA_DATA' && msg.data) {
            payload = msg.data;
            const progress = payload.progress || {};
            currentTime = progress.watched;
            // MEDIA_DATA doesn't include an event type — treat as a progress sync
            eventType = 'timeupdate';
            // For TV shows, extract season/episode from show_progress
            if (payload.type === 'tv' && payload.last_season_watched && payload.last_episode_watched) {
                payload.season = parseInt(payload.last_season_watched, 10);
                payload.episode = parseInt(payload.last_episode_watched, 10);
            }
        }
        // Format 3: VidKing stringified payload with top-level event field
        // { event: 'timeupdate', currentTime, duration, id, mediaType, ... }
        else if (msg.event && msg.currentTime != null) {
            payload = msg;
            eventType = msg.event;
            currentTime = msg.currentTime;
        }

        if (!eventType || currentTime == null) return;

        // Provider sends messages — disable fallback polling
        this._lastMessageAt = Date.now();
        this._everReceivedMsg = true;
        this._stopFallbackPoll();

        const completed = eventType === 'ended';
        // 10s throttle for in-progress events; always post on completion.
        if (!completed) {
            const now = Date.now();
            if (now - this._lastPostAt < 10000) return;
            this._lastPostAt = now;
        }

        const seasonNumber = payload.season != null
            ? parseInt(payload.season, 10)
            : (this.selectedEpisode
                ? this.content?.seasons?.[this.selectedSeasonIndex]?.season_number ?? null
                : null);
        const episodeNumber = payload.episode != null
            ? parseInt(payload.episode, 10)
            : this.selectedEpisode?.episode_number ?? null;

        historyApi.postProgress({
            content_type: this.contentType,
            tmdb_id: this.content.tmdb_id,
            progress_seconds: Math.round(Number(currentTime) || 0),
            completed,
            season_number: Number.isFinite(seasonNumber) ? seasonNumber : null,
            episode_number: Number.isFinite(episodeNumber) ? episodeNumber : null,
        }).catch(() => {});
    },
}));

Alpine.data('watchlistPage', () => ({
    items: [],
    continueItems: [],
    loading: false,
    error: '',
    activeFilter: 'all',

    init() {
        document.addEventListener('page:switch', (e) => {
            if (e.detail.pageId === 'watchlists') {
                this.loadWatchlist();
                this.loadContinueWatching();
            }
        });
    },

    async loadWatchlist() {
        if (!Alpine.store('auth').isLoggedIn) return;
        this.loading = true;
        this.error = '';
        try {
            const rawItems = await watchlistApi.getAll();
            const enriched = await Promise.allSettled(
                rawItems.map(async (item) => {
                    try {
                        let content;
                        try {
                            content = item.content_type === 'series'
                                ? await contentApi.getSeries(item.tmdb_id)
                                : await contentApi.getMovie(item.tmdb_id);
                        } catch (fetchErr) {
                            if (String(fetchErr.message).includes('404')) {
                                content = item.content_type === 'series'
                                    ? await contentApi.getMovie(item.tmdb_id)
                                    : await contentApi.getSeries(item.tmdb_id);
                                item.content_type = item.content_type === 'series' ? 'movie' : 'series';
                            } else {
                                throw fetchErr;
                            }
                        }
                        item._title = content.title || content.name || 'Unknown';
                        item._poster = content.poster_path
                            ? `https://image.tmdb.org/t/p/w500${content.poster_path}`
                            : null;
                        item._rating = content.vote_average || null;
                        item._runtime = content.runtime || null;
                    } catch {
                        item._title = item.content_type + ' ' + item.tmdb_id;
                        item._poster = null;
                        item._rating = null;
                        item._runtime = null;
                    }
                    return item;
                })
            );
            this.items = enriched.filter(r => r.status === 'fulfilled').map(r => r.value);
        } catch (e) {
            this.error = e.message;
        } finally {
            this.loading = false;
        }
    },

    async loadContinueWatching() {
        if (!Alpine.store('auth').isLoggedIn) return;
        try {
            const historyItems = await historyApi.getContinueWatching(20);
            const enriched = await Promise.allSettled(
                historyItems.map(async (item) => {
                    try {
                        let content;
                        try {
                            content = item.content_type === 'series'
                                ? await contentApi.getSeries(item.tmdb_id)
                                : await contentApi.getMovie(item.tmdb_id);
                        } catch (fetchErr) {
                            // If fetch fails with 404, try the other content type
                            if (String(fetchErr.message).includes('404')) {
                                content = item.content_type === 'series'
                                    ? await contentApi.getMovie(item.tmdb_id)
                                    : await contentApi.getSeries(item.tmdb_id);
                                // Correct the content_type for future navigations
                                item.content_type = item.content_type === 'series' ? 'movie' : 'series';
                            } else {
                                throw fetchErr;
                            }
                        }
                        item._title = content.title || content.name || 'Unknown';
                        item._poster = content.poster_path
                            ? `https://image.tmdb.org/t/p/w500${content.poster_path}`
                            : null;
                        item._rating = content.vote_average || null;
                        item._runtime = content.runtime || null;
                    } catch {
                        item._title = item.content_type + ' ' + item.tmdb_id;
                        item._poster = null;
                        item._rating = null;
                        item._runtime = null;
                    }
                    return item;
                })
            );
            this.continueItems = enriched.filter(r => r.status === 'fulfilled').map(r => r.value);
        } catch {
            this.continueItems = [];
        }
    },

    get filteredItems() {
        if (this.activeFilter === 'continue') return this.continueItems;
        if (this.activeFilter === 'favorites') return this.items.filter(i => i.is_favorite);
        const map = { watchlist: 'plan_to_watch', completed: 'completed' };
        const status = map[this.activeFilter];
        return status ? this.items.filter(i => i.status === status) : this.items;
    },

    statusLabel(item) {
        if (item.status === 'completed') return 'Completed';
        if (item.status === 'plan_to_watch') return 'Watchlist';
        return (item.status || '').replace(/_/g, ' ');
    },

    async toggleFavorite(item) {
        const next = !item.is_favorite;
        try {
            await watchlistApi.update(item._id, { is_favorite: next });
            item.is_favorite = next;
            Alpine.store('toast').show(next ? 'Added to Favorites!' : 'Removed from Favorites.');
        } catch (e) {
            Alpine.store('toast').show('Error: ' + e.message);
        }
    },

    getProgressPercent(item) {
        if (!item._runtime || !item.progress_seconds) return 0;
        const totalSec = item._runtime * 60;
        return Math.min(100, Math.round((item.progress_seconds / totalSec) * 100));
    },

    getProgressLabel(item) {
        if (!item.progress_seconds) return '';
        const mins = Math.floor(item.progress_seconds / 60);
        if (item._runtime) return `${mins}m / ${item._runtime}m`;
        return `${mins}m watched`;
    },

    async remove(item) {
        try {
            await watchlistApi.remove(item._id);
            this.items = this.items.filter(i => i._id !== item._id);
            Alpine.store('toast').show('Removed from Watchlist.');
        } catch (e) {
            Alpine.store('toast').show('Error: ' + e.message);
        }
    },

    navigateTo(item) {
        switchPage('detail', { contentId: item.tmdb_id, contentType: item.content_type });
    },
}));

Alpine.data('adminPage', () => ({
    activeTab: 'movies',
    loading: false,
    error: '',
    movies: [],
    comments: [],
    users: [],
    genres: [],
    movieSearch: '',
    userSearch: '',
    genreSearch: '',
    _moviesLoaded: false,
    _commentsLoaded: false,
    _usersLoaded: false,
    _genresLoaded: false,

    init() {
        document.addEventListener('page:switch', (e) => {
            if (e.detail.pageId === 'admin') {
                this._moviesLoaded = false;
                this._commentsLoaded = false;
                this._usersLoaded = false;
                this._genresLoaded = false;
                this.loadMovies();
            }
        });
    },

    async loadMovies() {
        if (this._moviesLoaded) return;
        this.loading = true;
        this.error = '';
        try {
            this.movies = await adminApi.getMovies();
            this._moviesLoaded = true;
        } catch (e) {
            this.error = 'Failed to load movies: ' + e.message;
        } finally {
            this.loading = false;
        }
    },

    async loadComments() {
        if (this._commentsLoaded) return;
        this.loading = true;
        this.error = '';
        try {
            this.comments = await adminApi.getComments();
            this._commentsLoaded = true;
        } catch (e) {
            this.error = 'Failed to load comments: ' + e.message;
        } finally {
            this.loading = false;
        }
    },

    async loadUsers() {
        if (this._usersLoaded) return;
        this.loading = true;
        this.error = '';
        try {
            this.users = await adminApi.getUsers();
            this._usersLoaded = true;
        } catch (e) {
            this.error = 'Failed to load users: ' + e.message;
        } finally {
            this.loading = false;
        }
    },

    async loadGenres() {
        if (this._genresLoaded) return;
        this.loading = true;
        this.error = '';
        try {
            this.genres = await adminApi.getGenres();
            this._genresLoaded = true;
        } catch (e) {
            this.error = 'Failed to load genres: ' + e.message;
        } finally {
            this.loading = false;
        }
    },

    get filteredMovies() {
        if (!this.movieSearch.trim()) return this.movies;
        const q = this.movieSearch.toLowerCase();
        return this.movies.filter(m =>
            (m.title || '').toLowerCase().includes(q) ||
            String(m.tmdb_id).includes(q)
        );
    },

    get filteredUsers() {
        if (!this.userSearch.trim()) return this.users;
        const q = this.userSearch.toLowerCase();
        return this.users.filter(u =>
            (u.email || '').toLowerCase().includes(q) ||
            (u.username || '').toLowerCase().includes(q)
        );
    },

    get filteredGenres() {
        if (!this.genreSearch.trim()) return this.genres;
        const q = this.genreSearch.toLowerCase();
        return this.genres.filter(g =>
            (g.name || '').toLowerCase().includes(q) ||
            String(g.genre_id).includes(q)
        );
    },

    async toggleGenreVisibility(genre) {
        try {
            const res = await adminApi.toggleGenreVisibility(genre.genre_id, !genre.is_hidden);
            genre.is_hidden = res.is_hidden;
            Alpine.store('toast').show(genre.is_hidden ? 'Genre hidden from users' : 'Genre is now visible');
        } catch (e) {
            Alpine.store('toast').show('Error: ' + e.message);
        }
    },

    async toggleMovieVisibility(movie) {
        try {
            const res = await adminApi.toggleMovieVisibility(movie.tmdb_id, !movie.is_hidden);
            movie.is_hidden = res.is_hidden;
            Alpine.store('toast').show(movie.is_hidden ? 'Movie hidden from users' : 'Movie is now visible');
        } catch (e) {
            Alpine.store('toast').show('Error: ' + e.message);
        }
    },

    async deleteComment(comment) {
        try {
            await adminApi.deleteComment(comment._id);
            this.comments = this.comments.filter(c => c._id !== comment._id);
            Alpine.store('toast').show('Comment deleted');
        } catch (e) {
            Alpine.store('toast').show('Error: ' + e.message);
        }
    },

    async toggleBan(user) {
        try {
            const res = await adminApi.banUser(user._id, !user.is_banned);
            user.is_banned = res.is_banned;
            Alpine.store('toast').show(user.is_banned ? 'User banned' : 'User unbanned');
        } catch (e) {
            Alpine.store('toast').show('Error: ' + e.message);
        }
    },
}));

Alpine.data('profilePage', () => ({
    stats: { watchlist_count: 0, completed_count: 0, ratings_count: 0, history_count: 0, average_rating: 0 },
    recentActivity: [],
    editUsername: '',
    editAvatar: '',
    saving: false,
    saveMsg: '',
    loading: false,
    activeTab: 'edit',

    // Change password state
    currentPassword: '',
    newPassword: '',
    confirmPassword: '',
    changingPassword: false,
    passwordMsg: '',
    passwordMsgClass: '',

    init() {
        document.addEventListener('page:switch', (e) => {
            if (e.detail.pageId === 'profile') this.loadProfile();
        });
    },

    async loadProfile() {
        if (!Alpine.store('auth').isLoggedIn) return;
        this.loading = true;
        try {
            const [statsData, activityData] = await Promise.all([
                apiFetch('/api/profile/stats'),
                apiFetch('/api/profile/recent-activity?limit=10'),
            ]);
            this.stats = statsData;
            this.recentActivity = activityData || [];
            this.editUsername = Alpine.store('auth').user?.username || '';
            this.editAvatar = Alpine.store('auth').user?.avatar_url || '';
        } catch (e) {
            Alpine.store('toast').show('Failed to load profile: ' + e.message);
        } finally {
            this.loading = false;
        }
    },

    async saveProfile() {
        this.saving = true;
        this.saveMsg = '';
        try {
            const data = await apiFetch('/api/profile/', {
                method: 'PATCH',
                body: JSON.stringify({
                    username: this.editUsername || undefined,
                    avatar_url: this.editAvatar || undefined,
                }),
            });
            // Update the auth store
            const auth = Alpine.store('auth');
            if (auth.user) {
                auth.user.username = data.username;
                auth.user.avatar_url = data.avatar_url;
            }
            this.saveMsg = 'Profile updated!';
            setTimeout(() => { this.saveMsg = ''; }, 3000);
        } catch (e) {
            Alpine.store('toast').show('Error: ' + e.message);
        } finally {
            this.saving = false;
        }
    },

    async changePassword() {
        this.passwordMsg = '';
        this.passwordMsgClass = '';

        if (!this.currentPassword || !this.newPassword || !this.confirmPassword) {
            this.passwordMsg = 'Please fill in all fields.';
            this.passwordMsgClass = 'msg-error';
            return;
        }
        if (this.newPassword.length < 6) {
            this.passwordMsg = 'New password must be at least 6 characters.';
            this.passwordMsgClass = 'msg-error';
            return;
        }
        if (this.newPassword !== this.confirmPassword) {
            this.passwordMsg = 'Passwords do not match.';
            this.passwordMsgClass = 'msg-error';
            return;
        }

        this.changingPassword = true;
        try {
            await apiFetch('/api/profile/change-password', {
                method: 'POST',
                body: JSON.stringify({
                    current_password: this.currentPassword,
                    new_password: this.newPassword,
                }),
            });
            this.passwordMsg = 'Password updated successfully!';
            this.passwordMsgClass = 'msg-success';
            this.currentPassword = '';
            this.newPassword = '';
            this.confirmPassword = '';
            setTimeout(() => { this.passwordMsg = ''; }, 3000);
        } catch (e) {
            this.passwordMsg = e.message || 'Failed to update password.';
            this.passwordMsgClass = 'msg-error';
        } finally {
            this.changingPassword = false;
        }
    },
}));

// Start Alpine
Alpine.start();

// --- DOM Ready ---
document.addEventListener('DOMContentLoaded', async () => {
    // Run preloader animation while pages load
    await initPreloader(pages_ready);

    // Wait for fetchUser (started by appState.init) to settle
    // so we know the auth state before choosing the initial page.
    await new Promise(r => setTimeout(r, 300));

    if (Alpine.store('auth').isLoggedIn) {
        switchPage('discover');
    } else {
        switchPage('login');
    }

    document.addEventListener('auth:expired', () => {
        Alpine.store('auth').logout();
        switchPage('login');
    });

    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const targetPage = link.getAttribute('data-page');
            if (targetPage) switchPage(targetPage);
        });
    });

    document.addEventListener('click', (e) => {
        // 1. Movie Card Click -> Go to Detail
        const movieCard = e.target.closest('.movie-card');
        if (movieCard && !e.target.closest('.bookmark-btn') && !e.target.closest('.episode-card')) {
            const tmdbId = parseInt(movieCard.dataset.tmdbId);
            const contentType = movieCard.dataset.contentType || 'movie';
            if (tmdbId) {
                switchPage('detail', { contentId: tmdbId, contentType });
            } else {
                switchPage('detail');
            }
            return;
        }

        // 2. Watch Now Button or Episode Card -> Go to Watching
        const epCard = e.target.closest('.episode-card');
        const watchBtn = e.target.closest('#btn-watch-now') || epCard;
        if (watchBtn) {
            switchPage('watching');
            return;
        }

        // 3. Mobile Menu Toggle
        const mobileMenuBtn = e.target.closest('#mobile-menu-btn');
        if (mobileMenuBtn) {
            const navLinksContainer = document.querySelector('.nav-links');
            if (navLinksContainer) navLinksContainer.classList.toggle('active');
        }

        // 5. Bookmarking from card grids (outside detailPage component)
        const bookmarkBtn = e.target.closest('.bookmark-btn');
        if (bookmarkBtn) {
            const card = bookmarkBtn.closest('.movie-card');
            if (!card) return;
            const tmdbId = parseInt(card.dataset.tmdbId);
            const contentType = card.dataset.contentType || 'movie';

            if (!Alpine.store('auth').isLoggedIn) {
                switchPage('login');
                return;
            }

            bookmarkBtn.classList.toggle('active');
            const isAdding = bookmarkBtn.classList.contains('active');

            if (isAdding) {
                bookmarkBtn.style.background = 'var(--accent-gold)';
                const icon = bookmarkBtn.querySelector('svg');
                if (icon) icon.style.fill = 'black';
                watchlistApi.add(contentType, tmdbId, 'plan_to_watch')
                    .then(() => Alpine.store('toast').show('Added to Watchlist!'))
                    .catch(err => {
                        bookmarkBtn.classList.remove('active');
                        bookmarkBtn.style.background = '';
                        Alpine.store('toast').show('Error: ' + err.message);
                    });
            } else {
                bookmarkBtn.style.background = '';
                const icon = bookmarkBtn.querySelector('svg');
                if (icon) icon.style.fill = 'none';
                watchlistApi.getAll()
                    .then(items => {
                        const item = items.find(i => i.tmdb_id === tmdbId && i.content_type === contentType);
                        if (item) return watchlistApi.remove(item._id);
                    })
                    .then(() => Alpine.store('toast').show('Removed from Watchlist.'))
                    .catch(err => Alpine.store('toast').show('Error: ' + err.message));
            }
        }
    });
});
