/**
 * Home page rails — each rail is a horizontal row of content cards.
 * Returns a structured object the frontend can render directly.
 */
declare function get_home_rails(user_id?: string): Promise<{
    rails: Record<string, unknown>[];
    genres: (import("./models/Genre.js").GenreDoc & Required<{
        _id: import("mongoose").Types.ObjectId;
    }> & {
        __v: number;
    })[];
}>;
/**
 * Genre-filtered browse page data.
 */
declare function get_content_by_genre(genre_id: number, page?: number, limit?: number): Promise<{
    movies: (import("./models/Movie.js").MovieDoc & Required<{
        _id: import("mongoose").Types.ObjectId;
    }> & {
        __v: number;
    })[];
    series: (import("./models/Series.js").SeriesDoc & Required<{
        _id: import("mongoose").Types.ObjectId;
    }> & {
        __v: number;
    })[];
    pagination: {
        page: number;
        limit: number;
        total_movies: number;
        total_series: number;
        has_more_movies: boolean;
        has_more_series: boolean;
    };
}>;
/**
 * Profile statistics for an authenticated user.
 */
declare function get_profile_stats(user_id: string): Promise<{
    watchlist_count: number;
    completed_count: number;
    watching_count: number;
    ratings_count: number;
    history_count: number;
    average_rating: number;
}>;
/**
 * Recent activity feed for profile page.
 */
declare function get_recent_activity(user_id: string, limit?: number): Promise<{
    recent_history: (import("./models/WatchHistory.js").WatchHistoryDoc & Required<{
        _id: import("mongoose").Types.ObjectId;
    }> & {
        __v: number;
    })[];
    recent_ratings: (import("./models/UserRating.js").UserRatingDoc & Required<{
        _id: import("mongoose").Types.ObjectId;
    }> & {
        __v: number;
    })[];
    recent_watchlist: (import("./models/WatchlistItem.js").WatchlistItemDoc & Required<{
        _id: import("mongoose").Types.ObjectId;
    }> & {
        __v: number;
    })[];
}>;
export { get_home_rails, get_content_by_genre, get_profile_stats, get_recent_activity };
//# sourceMappingURL=libraryService.d.ts.map