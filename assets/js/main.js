/**
 * CineDrop Main
 * Application entry point and event delegation
 */

document.addEventListener('DOMContentLoaded', async () => {
    
    // Wait for page fragments to be loaded into the DOM
    if (window.pages_ready) await window.pages_ready;

    // Switch to login page on first load
    if (window.switchPage) window.switchPage('login');

    // Initialize specific modules
    if (window.initSearch) window.initSearch();
    if (window.initFilters) window.initFilters();

    const navLinks = document.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const targetPage = link.getAttribute('data-page');
            if (targetPage && window.switchPage) window.switchPage(targetPage);
        });
    });

    // --- Global Click Interactivity ---
    document.addEventListener('click', (e) => {
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
                // Update Metadata for Player
                const epTitle = epCard.querySelector('h3').innerText;
                const epDesc = epCard.querySelector('p').innerText;
                const playerTitle = document.querySelector('.player-title');
                const playerDesc = document.querySelector('#page-watching .detail-desc');
                if (playerTitle) playerTitle.innerText = epTitle;
                if (playerDesc) playerDesc.innerText = epDesc;
            }
            window.switchPage('watching');
            return;
        }

        // 3. Login Button -> Go to Discover
        const loginBtn = e.target.closest('#btn-login-continue');
        if (loginBtn) {
            window.switchPage('discover');
            return;
        }

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
