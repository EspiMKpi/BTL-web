/**
 * CineDrop Actions
 * Handles search, filters, and user feedback
 */

window.showNotification = function(message) {
    let toast = document.getElementById('toast-container');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'toast-container';
        toast.style.cssText = `
            position: fixed;
            bottom: 30px;
            right: 30px;
            background: var(--accent-gold);
            color: black;
            padding: 12px 24px;
            border-radius: 12px;
            font-weight: 600;
            z-index: 2000;
            transform: translateY(100px);
            transition: transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        `;
        document.body.appendChild(toast);
    }
    toast.innerText = message;
    toast.style.transform = 'translateY(0)';
    setTimeout(() => {
        toast.style.transform = 'translateY(100px)';
    }, 3000);
};

window.initSearch = function() {
    const searchInputs = document.querySelectorAll('.search-box input, .filter-search input');
    searchInputs.forEach(input => {
        input.addEventListener('input', (e) => {
            const query = e.target.value.toLowerCase();
            const allCards = document.querySelectorAll('.movie-card');
            
            allCards.forEach(card => {
                const titleText = card.querySelector('.card-title')?.innerText.toLowerCase() || "";
                card.style.display = titleText.includes(query) ? 'block' : 'none';
            });
        });
    });
};

window.initFilters = function() {
    const filterCheckboxes = document.querySelectorAll('.filter-group input[type="checkbox"]');
    filterCheckboxes.forEach(cb => {
        cb.addEventListener('change', () => {
            const activeGenres = Array.from(document.querySelectorAll('.filter-group:nth-child(2) input:checked')).map(i => i.parentElement.innerText.trim().toLowerCase());
            const activeYears = Array.from(document.querySelectorAll('.filter-group:nth-child(1) input:checked')).map(i => i.parentElement.innerText.trim().toLowerCase());
            const activeTypes = Array.from(document.querySelectorAll('.filter-group:nth-child(3) input:checked')).map(i => i.parentElement.innerText.trim().toLowerCase());

            const allCards = document.querySelectorAll('#search-results-grid .movie-card');
            allCards.forEach(card => {
                const infoText = card.querySelector('.card-info').innerText.toLowerCase();
                const genreMatch = activeGenres.length === 0 || activeGenres.some(g => infoText.includes(g));
                const yearMatch = activeYears.length === 0 || activeYears.some(y => infoText.includes(y));
                const typeMatch = activeTypes.length === 0 || activeTypes.some(t => infoText.includes(t.replace(' series', '')));

                card.style.display = (genreMatch && yearMatch && typeMatch) ? 'block' : 'none';
            });
        });
    });

    const filterToggle = document.getElementById('filter-dropdown-toggle');
    const filterPanel = document.getElementById('filter-panel');
    if (filterToggle && filterPanel) {
        filterToggle.addEventListener('click', () => {
            filterPanel.classList.toggle('active');
        });
    }
};
