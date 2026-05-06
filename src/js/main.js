/**
 * CineDrop Main
 * Application entry point with Alpine.js reactivity
 */

import Alpine from 'alpinejs';
import { pages_ready } from './pages.js';
import { switchPage } from './router.js';
import { showNotification, initSearch, initFilters } from './actions.js';

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
        if (!res.ok) throw new Error(data.error);
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
        if (!res.ok) throw new Error(data.error);
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

Alpine.data('filterPanel', () => ({
    open: false,
    toggle() { this.open = !this.open; }
}));

Alpine.data('faqItem', () => ({
    open: false,
    toggle() { this.open = !this.open; }
}));

// Start Alpine
Alpine.start();

// --- DOM Ready ---
document.addEventListener('DOMContentLoaded', async () => {
    await pages_ready;
    switchPage('login');
    initSearch();
    initFilters();

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
            switchPage('detail');
            return;
        }

        // 2. Watch Now Button or Episode Card -> Go to Watching
        const epCard = e.target.closest('.episode-card');
        const watchBtn = e.target.closest('#btn-watch-now') || e.target.closest('.hero .btn-primary') || epCard;
        if (watchBtn) {
            if (epCard) {
                const epTitle = epCard.querySelector('h3').innerText;
                const epDesc = epCard.querySelector('p').innerText;
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

        // 7. Bookmarking Logic
        const bookmarkBtn = e.target.closest('.bookmark-btn');
        if (bookmarkBtn) {
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
                    const status = card.querySelector('.card-status')?.innerText.toLowerCase();
                    card.style.display = (tabName === 'all' || (status && status.includes(tabName))) ? 'block' : 'none';
                });
            }
        }
    });
});
