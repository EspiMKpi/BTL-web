/**
 * CineDrop Main
 * Application entry point and event delegation
 */

document.addEventListener('DOMContentLoaded', () => {
    window.onPageRendered = () => {
        if (window.initSearch) window.initSearch();
        if (window.initFilters) window.initFilters();
    };

    if (window.bootstrapRouter) {
        window.bootstrapRouter();
    }

    // --- Global Click Interactivity ---
    document.addEventListener('click', (e) => {
        // 0. Navigation links -> Route to page
        const navLink = e.target.closest('.nav-link');
        if (navLink) {
            e.preventDefault();
            const targetPage = navLink.getAttribute('data-page');
            if (targetPage && window.switchPage) {
                window.switchPage(targetPage);
            }
            return;
        }

        // 1. Movie Card Click -> Go to Detail
        const movieCard = e.target.closest('.movie-card');
        if (movieCard && !e.target.closest('.bookmark-btn') && !e.target.closest('.episode-card')) {
            window.switchPage('detail');
            return;
        }

        // 2. Watch Now Button or Episode Card -> Go to Watching
        const epCard = e.target.closest('.episode-card');
        const watchBtn = e.target.closest('#btn-watch-now') || e.target.closest('.hero .btn-primary') || epCard;
        
        if (watchBtn) {
            if (epCard) {
                window.appState = window.appState || {};
                const epTitle = epCard.querySelector('h3').innerText;
                const epDesc = epCard.querySelector('p').innerText;
                window.appState.playerOverride = {
                    title: epTitle,
                    description: epDesc
                };
            } else if (window.appState) {
                window.appState.playerOverride = null;
            }
            window.switchPage('watching');
            return;
        }

        // 3. Login Button -> Go to Discover
        const loginBtn = e.target.closest('#btn-login-continue');
        if (loginBtn) {
            if (window.appState) window.appState.playerOverride = null;
            window.switchPage('discover');
            return;
        }

        // 3b. Register Button -> Go to Discover
        const registerBtn = e.target.closest('#btn-register-continue');
        if (registerBtn) {
            if (window.appState) window.appState.playerOverride = null;
            window.switchPage('discover');
            return;
        }

        // 3c. Auth navigation (Login <-> Register)
        const toRegister = e.target.closest('#link-to-register');
        if (toRegister) { e.preventDefault(); window.switchPage('register'); return; }

        const toLogin = e.target.closest('#link-to-login');
        if (toLogin) { e.preventDefault(); window.switchPage('login'); return; }

        // 4. Avatar Toggle -> Open Dropdown
        const avatarToggle = e.target.closest('#avatar-toggle');
        const dropdown = document.getElementById('profile-dropdown');
        if (avatarToggle && dropdown) {
            dropdown.classList.toggle('show');
            return;
        }

        // 5. Logout Button -> Go to Login
        const logoutBtn = e.target.closest('#logout-btn');
        if (logoutBtn) {
            window.switchPage('login');
            return;
        }

        // 6. Click Outside Dropdown -> Close it
        if (dropdown && dropdown.classList.contains('show') && !e.target.closest('.avatar-wrapper')) {
            dropdown.classList.remove('show');
        }

        // 6b. Mobile Menu Toggle
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
                window.showNotification("Added to Watchlist!");
            } else {
                bookmarkBtn.style.background = 'rgba(122, 120, 128, 0.5)';
                if (icon) icon.style.fill = 'none';
                window.showNotification("Removed from Watchlist.");
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
            
            // Trigger specific action if list tab
            const tabName = tab.innerText.toLowerCase();
            const watchlistGrid = document.querySelector('.watchlist-grid');
            if (tab.classList.contains('list-tab') && watchlistGrid) {
                const cards = watchlistGrid.querySelectorAll('.movie-card');
                cards.forEach(card => {
                    const status = card.querySelector('.card-status')?.innerText.toLowerCase();
                    if (tabName === 'all' || (status && status.includes(tabName)) || (tabName === 'continue watching' && status && status.includes('result'))) {
                        card.style.display = 'block';
                    } else {
                        card.style.display = 'none';
                    }
                });
            }
        }
    });

});
