/**
 * CineDrop Router
 * Handles page switching and navigation state
 */

export function switchPage(pageId, params = {}) {
    const navLinks = document.querySelectorAll('.nav-link');
    const pages = document.querySelectorAll('.page-content');
    const nav = document.getElementById('main-nav');
    const footer = document.querySelector('.main-footer');
    const dropdown = document.getElementById('profile-dropdown');
    const navLinksContainer = document.querySelector('.nav-links');

    pages.forEach(page => {
        page.classList.remove('active');
        if (page.id === `page-${pageId}`) {
            page.classList.add('active');
        }
    });

    if (pageId === 'login' || pageId === 'register') {
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

    if (pageId === 'series') {
        const seriesPage = document.getElementById('page-series');
        if (seriesPage) seriesPage.classList.add('active');
    }

    if (dropdown) dropdown.classList.remove('show');
    if (navLinksContainer) navLinksContainer.classList.remove('active');

    if (window.Alpine) {
        const nav = window.Alpine.store('nav');
        if (nav) {
            nav.currentPage = pageId;
            if (params.contentId !== undefined) nav.contentId = params.contentId;
            if (params.contentType !== undefined) nav.contentType = params.contentType;
        }
    }

    document.dispatchEvent(new CustomEvent('page:switch', { detail: { pageId, params } }));

    window.scrollTo({ top: 0, behavior: 'smooth' });
}
