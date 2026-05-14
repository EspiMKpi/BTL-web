/**
 * CineDrop Router
 * Handles page switching with anime.js-powered transitions and hash-based
 * URL sync so browser Back/Forward and deep links work.
 */

import { pageTransitionOut, pageTransitionIn, initScrollReveals, cleanupScrollReveals } from './animations.js';

let isTransitioning = false;
let suppressHashChange = false;

/** Pages that map to a bare `#/pageId` hash. */
const SIMPLE_PAGES = ['landing', 'login', 'register', 'discover', 'movies', 'series', 'watchlists', 'profile', 'admin'];
/** Pages that carry a content target in the hash. */
const CONTENT_PAGES = ['detail', 'watching'];

const PAGE_LABELS = {
    discover: 'Discover', movies: 'Movies', series: 'Series',
    watchlists: 'My Watchlists', profile: 'Profile', admin: 'Admin panel',
    detail: 'Title details', watching: 'Now playing',
    login: 'Sign in', register: 'Create account', landing: 'Welcome',
};

/** Build the canonical hash for a page + params. */
export function buildHash(pageId, params = {}) {
    if (CONTENT_PAGES.includes(pageId) && params.contentId != null) {
        const ct = params.contentType || 'movie';
        return `#/${pageId}/${ct}/${params.contentId}`;
    }
    return `#/${pageId}`;
}

/** Parse the current location hash into { pageId, params } or null if invalid. */
export function parseHash() {
    const raw = (window.location.hash || '').replace(/^#\/?/, '');
    if (!raw) return null;
    const parts = raw.split('/').filter(Boolean);
    const pageId = parts[0];
    if (CONTENT_PAGES.includes(pageId)) {
        const contentId = Number(parts[2]);
        if (!contentId) return null;
        return { pageId, params: { contentType: parts[1] || 'movie', contentId } };
    }
    if (SIMPLE_PAGES.includes(pageId)) return { pageId, params: {} };
    return null;
}

function syncHash(pageId, params) {
    const next = buildHash(pageId, params);
    if (window.location.hash === next) return;
    suppressHashChange = true;
    window.location.hash = next;
}

function announcePage(pageId) {
    const announcer = document.getElementById('sr-announcer');
    if (announcer) announcer.textContent = (PAGE_LABELS[pageId] || pageId) + ' page';
}

/**
 * Wire the hashchange listener. Call once from main.js after pages are ready.
 */
export function initRouter() {
    suppressHashChange = false;
    window.addEventListener('hashchange', () => {
        if (suppressHashChange) {
            suppressHashChange = false;
            return;
        }
        const parsed = parseHash();
        if (parsed) {
            switchPage(parsed.pageId, parsed.params, { fromHash: true });
        }
    });
}

export async function switchPage(pageId, params = {}, opts = {}) {
    if (isTransitioning && !opts.force) return;

    const pages = document.querySelectorAll('.page-content');
    const currentPage = document.querySelector('.page-content.active');
    const targetPage = document.getElementById(`page-${pageId}`);
    const nav = document.getElementById('main-nav');
    const footer = document.querySelector('.main-footer');
    const dropdown = document.getElementById('profile-dropdown');
    const navLinksContainer = document.querySelector('.nav-links');

    // Force switch: cancel any ongoing transition and do an instant swap.
    if (opts.force && isTransitioning) {
        isTransitioning = false;
        applySwitch(pages, pageId, params, nav, footer, dropdown, navLinksContainer);
        if (!opts.fromHash) syncHash(pageId, params);
        return;
    }

    // Same page already active.
    if (currentPage && targetPage && currentPage.id === targetPage.id) {
        const navStore = window.Alpine?.store('nav');
        const sameContent = params.contentId == null
            || (navStore && navStore.contentId === params.contentId);
        if (sameContent) {
            if (!opts.fromHash) syncHash(pageId, params);
            return;
        }
        // Same page, different content (e.g. detail → detail): re-apply without animation.
        applySwitch(pages, pageId, params, nav, footer, dropdown, navLinksContainer);
        if (!opts.fromHash) syncHash(pageId, params);
        return;
    }

    // --- Instant switch (no animation) for first load or missing elements ---
    if (!currentPage || !targetPage) {
        applySwitch(pages, pageId, params, nav, footer, dropdown, navLinksContainer);
        if (!opts.fromHash) syncHash(pageId, params);
        return;
    }

    // --- Animated transition with anime.js ---
    isTransitioning = true;

    // 1. Clean up scroll observers on current page
    cleanupScrollReveals();

    // 2. Animate out current page
    await pageTransitionOut(currentPage);

    // 3. Swap pages
    applySwitch(pages, pageId, params, nav, footer, dropdown, navLinksContainer);
    if (!opts.fromHash) syncHash(pageId, params);

    // 4. Animate in new page
    await pageTransitionIn(targetPage);

    // 5. Initialize scroll reveals on the new page
    initScrollReveals(targetPage);

    isTransitioning = false;
}

function applySwitch(pages, pageId, params, nav, footer, dropdown, navLinksContainer) {
    const navLinks = document.querySelectorAll('.nav-link');

    pages.forEach(page => {
        page.classList.remove('active', 'page-fade-out');
        if (page.id === `page-${pageId}`) {
            page.classList.add('active');
        }
    });

    if (pageId === 'login' || pageId === 'register' || pageId === 'landing') {
        if (nav) nav.classList.add('hide');
        if (footer) footer.classList.add('hide');
    } else {
        if (nav) nav.classList.remove('hide');
        if (footer) footer.classList.remove('hide');
    }

    navLinks.forEach(link => {
        link.classList.remove('active');
        if (link.getAttribute('data-page') === pageId) {
            link.classList.add('active');
        }
    });

    if (dropdown) dropdown.classList.remove('show');
    if (navLinksContainer) navLinksContainer.classList.remove('active');

    if (window.Alpine) {
        const alpineNav = window.Alpine.store('nav');
        if (alpineNav) {
            alpineNav.currentPage = pageId;
            if (params.contentId !== undefined) alpineNav.contentId = params.contentId;
            if (params.contentType !== undefined) alpineNav.contentType = params.contentType;
            if (params.seasonIndex !== undefined) alpineNav.seasonIndex = params.seasonIndex;
            if (params.episodeNumber !== undefined) alpineNav.episodeNumber = params.episodeNumber;
        }
    }

    document.dispatchEvent(new CustomEvent('page:switch', { detail: { pageId, params } }));
    announcePage(pageId);

    window.scrollTo({ top: 0, behavior: 'smooth' });
}
