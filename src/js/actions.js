/**
 * CineDrop Actions
 * Handles search, filters, and user feedback
 */

export function showNotification(message) {
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
}

export function initSearch() { /* search is now handled by moviesPage Alpine component */ }

export function initFilters() { /* filters are now handled by moviesPage Alpine component */ }
