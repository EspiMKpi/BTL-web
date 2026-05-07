async function apiFetch(endpoint, options = {}) {
    const token = localStorage.getItem('token');
    const headers = { ...options.headers };

    if (token) headers['Authorization'] = `Bearer ${token}`;
    if (options.body && typeof options.body === 'string') {
        headers['Content-Type'] = 'application/json';
    }

    const res = await fetch(endpoint, { ...options, headers });

    if (res.status === 401) {
        document.dispatchEvent(new CustomEvent('auth:expired'));
        throw new Error('Session expired. Please log in again.');
    }

    if (!res.ok) {
        let msg = `HTTP ${res.status}`;
        try {
            const body = await res.json();
            msg = body.detail || body.error || msg;
        } catch { /* ignore parse errors */ }
        throw new Error(msg);
    }

    if (res.status === 204) return null;
    return res.json();
}

export const contentApi = {
    getHome: () => apiFetch('/api/content/home'),
    getGenres: () => apiFetch('/api/content/genres'),
    browse: (genreId, page = 1, limit = 20) =>
        apiFetch(`/api/content/browse/${genreId}?page=${page}&limit=${limit}`),
    search: (query, page = 1, limit = 20) =>
        apiFetch(`/api/content/search?q=${encodeURIComponent(query)}&page=${page}&limit=${limit}`),
    getMovie: (id) => apiFetch(`/api/content/movie/${id}`),
    getSeries: (id) => apiFetch(`/api/content/series/${id}`),
};

export const watchlistApi = {
    getAll: () => apiFetch('/api/watchlist/'),
    add: (contentType, tmdbId, status = 'plan_to_watch') =>
        apiFetch('/api/watchlist/', {
            method: 'POST',
            body: JSON.stringify({ content_type: contentType, tmdb_id: tmdbId, status }),
        }),
    remove: (itemId) => apiFetch(`/api/watchlist/${itemId}`, { method: 'DELETE' }),
};

export const historyApi = {
    postProgress: (body) =>
        apiFetch('/api/history/progress', {
            method: 'POST',
            body: JSON.stringify(body),
        }),
};

export const commentsApi = {
    get: (tmdbId, contentType) =>
        apiFetch(`/api/comments/${tmdbId}${contentType ? '?content_type=' + contentType : ''}`),
    add: (contentType, tmdbId, text) =>
        apiFetch('/api/comments/', {
            method: 'POST',
            body: JSON.stringify({ content_type: contentType, tmdb_id: tmdbId, text }),
        }),
    remove: (commentId) =>
        apiFetch(`/api/comments/${commentId}`, { method: 'DELETE' }),
};

export const adminApi = {
    getUsers: (page = 1, limit = 50) =>
        apiFetch(`/api/admin/users?page=${page}&limit=${limit}`),
    banUser: (userId, isBanned) =>
        apiFetch(`/api/admin/users/${userId}/ban`, {
            method: 'PATCH',
            body: JSON.stringify({ is_banned: isBanned }),
        }),
    getMovies: (page = 1, limit = 50) =>
        apiFetch(`/api/admin/movies?page=${page}&limit=${limit}`),
    toggleMovieVisibility: (tmdbId, isHidden) =>
        apiFetch(`/api/admin/movies/${tmdbId}/visibility`, {
            method: 'PATCH',
            body: JSON.stringify({ is_hidden: isHidden }),
        }),
    getComments: (page = 1, limit = 50) =>
        apiFetch(`/api/admin/comments?page=${page}&limit=${limit}`),
    deleteComment: (commentId) =>
        apiFetch(`/api/admin/comments/${commentId}`, { method: 'DELETE' }),
};
