/**
 * VozFlix Router
 * Loads page fragments and handles navigation state
 */
const PAGE_FILES = {
    login: 'login.html',
    register: 'register.html',
    discover: 'discover.html',
    movies: 'movies.html',
    series: 'series.html',
    watchlists: 'watchlists.html',
    detail: 'detail.html',
    watching: 'watching.html'
};

const PAGE_CACHE = {};
const DEFAULT_PAGE = 'discover';

window.appState = window.appState || {
    currentPage: null,
    playerOverride: null
};

async function loadPageMarkup(pageId) {
    const host = document.getElementById('page-host');
    if (!host) return;

    if (!PAGE_CACHE[pageId]) {
        const response = await fetch(`pages/${PAGE_FILES[pageId]}`);
        if (!response.ok) {
            throw new Error(`Failed to load page '${pageId}'`);
        }
        PAGE_CACHE[pageId] = await response.text();
    }

    host.innerHTML = PAGE_CACHE[pageId];
    const renderedPage = host.querySelector('.page-content');
    if (renderedPage) renderedPage.classList.add('active');
}

function setLayoutVisibility(pageId) {
    const nav = document.getElementById('main-nav');
    const footer = document.querySelector('.main-footer');
    const isAuthPage = pageId === 'login' || pageId === 'register';

    if (nav) nav.classList.toggle('hide', isAuthPage);
    if (footer) footer.classList.toggle('hide', isAuthPage);
}

function setActiveNavLink(pageId) {
    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
        link.classList.toggle('active', link.getAttribute('data-page') === pageId);
    });
}

function cleanupTransientUi() {
    const dropdown = document.getElementById('profile-dropdown');
    const navLinksContainer = document.querySelector('.nav-links');
    if (dropdown) dropdown.classList.remove('show');
    if (navLinksContainer) navLinksContainer.classList.remove('active');
}

function applyWatchingOverride() {
    if (window.appState.currentPage !== 'watching' || !window.appState.playerOverride) {
        return;
    }

    const { title, description } = window.appState.playerOverride;
    const playerTitle = document.querySelector('.player-title');
    const playerDesc = document.querySelector('#page-watching .detail-desc');

    if (playerTitle && title) playerTitle.innerText = title;
    if (playerDesc && description) playerDesc.innerText = description;
}

window.switchPage = async function(pageId, options = {}) {
    const { pushHash = true } = options;
    const targetPage = PAGE_FILES[pageId] ? pageId : DEFAULT_PAGE;

    try {
        await loadPageMarkup(targetPage);
    } catch (error) {
        const host = document.getElementById('page-host');
        if (host) {
            host.innerHTML = '<div class="page-content active"><p style="padding: 30px 60px;">Unable to load this page.</p></div>';
        }
    }

    window.appState.currentPage = targetPage;
    setLayoutVisibility(targetPage);
    setActiveNavLink(targetPage);
    cleanupTransientUi();

    if (typeof window.onPageRendered === 'function') {
        window.onPageRendered(targetPage);
    }

    applyWatchingOverride();

    if (pushHash) {
        window.location.hash = targetPage;
    }

    window.scrollTo({ top: 0, behavior: 'smooth' });
};

window.bootstrapRouter = function() {
    const initialPage = window.location.hash.replace('#', '') || DEFAULT_PAGE;
    window.switchPage(initialPage, { pushHash: false });
};

window.addEventListener('hashchange', () => {
    const hashPage = window.location.hash.replace('#', '') || DEFAULT_PAGE;
    if (hashPage !== window.appState.currentPage) {
        window.switchPage(hashPage, { pushHash: false });
    }
});
