/**
 * CineDrop Router
 * Handles page switching and navigation state
 */

export function switchPage(pageId) {
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

    if (pageId === 'login') {
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

    window.scrollTo({ top: 0, behavior: 'smooth' });
}
