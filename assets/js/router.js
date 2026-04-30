/**
 * CineDrop Router
 * Handles page switching between standalone HTML files.
 */

const ROUTE_MAP = {
    landing: 'landing.html',
    login: 'auth-login.html',
    register: 'register.html',
    discover: 'discover.html',
    movies: 'movies.html',
    series: 'series.html',
    watchlists: 'watchlists.html',
    detail: 'detail.html',
    watching: 'watching.html'
};

window.switchPage = function(pageId) {
    const routeKey = String(pageId || '').toLowerCase();
    const targetPath = ROUTE_MAP[routeKey] || ROUTE_MAP.landing;
    const currentPath = window.location.pathname.split('/').pop().toLowerCase();

    if (currentPath === targetPath.toLowerCase()) return;
    window.location.href = targetPath;
};