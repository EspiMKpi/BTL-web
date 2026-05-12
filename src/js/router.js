/**
 * CineDrop Router
 * Handles page switching with anime.js-powered transitions
 */

import { pageTransitionOut, pageTransitionIn, initScrollReveals, cleanupScrollReveals } from './animations.js';

let isTransitioning = false;

export async function switchPage(pageId, params = {}) {
    if (isTransitioning) return;

    const pages = document.querySelectorAll('.page-content');
    const currentPage = document.querySelector('.page-content.active');
    const targetPage = document.getElementById(`page-${pageId}`);
    const nav = document.getElementById('main-nav');
    const footer = document.querySelector('.main-footer');
    const dropdown = document.getElementById('profile-dropdown');
    const navLinksContainer = document.querySelector('.nav-links');

    // Already on this page — skip
    if (currentPage && targetPage && currentPage.id === targetPage.id) return;

    // --- Instant switch (no animation) for first load or missing elements ---
    if (!currentPage || !targetPage) {
        applySwitch(pages, pageId, params, nav, footer, dropdown, navLinksContainer);
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
        }
    }

    document.dispatchEvent(new CustomEvent('page:switch', { detail: { pageId, params } }));

    window.scrollTo({ top: 0, behavior: 'smooth' });
}
