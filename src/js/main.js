import Alpine from 'alpinejs';
import { pages_ready } from './pages.js';
import { switchPage } from './router.js';
import { contentApi, watchlistApi, historyApi, adminApi, apiFetch } from './api.js';

window.Alpine = Alpine;
window.switchPage = switchPage;

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
        const data = await res.json();
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
        const data = await res.json();
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
                this.user = await res.json();
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

Alpine.data('discoverPage', () => ({
    rails: [],
    loading: false,
    error: '',

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
            this.rails = (data.rails || []).filter(r => r.items && r.items.length > 0);
        } catch (e) {
            this.error = e.message;
        } finally {
            this.loading = false;
        }
    },

    get top10Rail() {
        return this.rails.find(r => r.items && r.items.length >= 5) || this.rails[0] || null;
    },
    get top10() {
        return (this.top10Rail?.items || []).slice(0, 10);
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
            switchPage('movies');
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
            switchPage('movies');
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
        try {
            if (contentType === 'series') {
                this.content = await contentApi.getSeries(contentId);
            } else {
                this.content = await contentApi.getMovie(contentId);
            }
            await this.checkWatchlistStatus(contentId, contentType);
        } catch (e) {
            this.error = 'Failed to load: ' + e.message;
        } finally {
            this.loading = false;
        }
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
}));

Alpine.data('watchingPage', () => ({
    content: null,
    contentType: null,
    loading: false,
    error: '',
    selectedEpisode: null,
    selectedSeasonIndex: 0,
    _lastPostAt: 0,

    init() {
        document.addEventListener('page:switch', (e) => {
            if (e.detail.pageId !== 'watching') return;
            const params = e.detail.params || {};
            const contentId = params.contentId || Alpine.store('nav').contentId;
            const contentType = params.contentType || Alpine.store('nav').contentType || 'movie';
            this.load(contentId, contentType);
        });
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
        try {
            this.content = contentType === 'series'
                ? await contentApi.getSeries(contentId)
                : await contentApi.getMovie(contentId);
            if (contentType === 'series') {
                const eps = this.content?.seasons?.[0]?.episodes || [];
                this.selectedEpisode = eps[0] || null;
            }
        } catch (e) {
            this.error = 'Failed to load: ' + e.message;
        } finally {
            this.loading = false;
        }
    },

    selectEpisode(ep) {
        this.selectedEpisode = ep;
        this._lastPostAt = 0;
        const video = document.querySelector('#page-watching video');
        if (video) {
            video.currentTime = 0;
            video.play().catch(() => {});
        }
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
        const idx = eps.findIndex(e => e.episode_number === this.selectedEpisode.episode_number);
        return idx >= 0 ? eps.slice(idx + 1, idx + 5) : [];
    },

    episodeThumb(ep) {
        if (ep?.still_path) return `https://image.tmdb.org/t/p/w500${ep.still_path}`;
        if (this.content?.backdrop_path) return `https://image.tmdb.org/t/p/w500${this.content.backdrop_path}`;
        return 'https://placehold.co/500x281/1a1a2e/white?text=Episode';
    },

    onTimeUpdate(ev) {
        const now = Date.now();
        if (now - this._lastPostAt < 10000) return;
        this._lastPostAt = now;
        if (!Alpine.store('auth').isLoggedIn || !this.content?.tmdb_id) return;
        const seasonNumber = this.selectedEpisode
            ? this.content?.seasons?.[this.selectedSeasonIndex]?.season_number ?? null
            : null;
        historyApi.postProgress({
            content_type: this.contentType,
            tmdb_id: this.content.tmdb_id,
            progress_seconds: Math.floor(ev.target.currentTime || 0),
            completed: false,
            season_number: seasonNumber,
            episode_number: this.selectedEpisode?.episode_number ?? null,
        }).catch(() => {});
    },

    onEnded(ev) {
        if (!Alpine.store('auth').isLoggedIn || !this.content?.tmdb_id) return;
        const seasonNumber = this.selectedEpisode
            ? this.content?.seasons?.[this.selectedSeasonIndex]?.season_number ?? null
            : null;
        historyApi.postProgress({
            content_type: this.contentType,
            tmdb_id: this.content.tmdb_id,
            progress_seconds: Math.floor(ev.target.currentTime || 0),
            completed: true,
            season_number: seasonNumber,
            episode_number: this.selectedEpisode?.episode_number ?? null,
        }).catch(() => {});
    },
}));

Alpine.data('watchlistPage', () => ({
    items: [],
    loading: false,
    error: '',
    activeFilter: 'all',

    init() {
        document.addEventListener('page:switch', (e) => {
            if (e.detail.pageId === 'watchlists') this.loadWatchlist();
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
                        const content = item.content_type === 'series'
                            ? await contentApi.getSeries(item.tmdb_id)
                            : await contentApi.getMovie(item.tmdb_id);
                        item._title = content.title || content.name || 'Unknown';
                        item._poster = content.poster_path
                            ? `https://image.tmdb.org/t/p/w500${content.poster_path}`
                            : null;
                        item._rating = content.vote_average || null;
                    } catch {
                        item._title = item.content_type + ' ' + item.tmdb_id;
                        item._poster = null;
                        item._rating = null;
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

    get filteredItems() {
        const map = { continue: 'watching', wishlist: 'plan_to_watch', completed: 'completed', favorites: 'favorites' };
        const status = map[this.activeFilter];
        return status ? this.items.filter(i => i.status === status) : this.items;
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
    movieSearch: '',
    userSearch: '',
    _moviesLoaded: false,
    _commentsLoaded: false,
    _usersLoaded: false,

    init() {
        document.addEventListener('page:switch', (e) => {
            if (e.detail.pageId === 'admin') {
                this._moviesLoaded = false;
                this._commentsLoaded = false;
                this._usersLoaded = false;
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
}));

// Start Alpine
Alpine.start();

// --- DOM Ready ---
document.addEventListener('DOMContentLoaded', async () => {
    await pages_ready;

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
