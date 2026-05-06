import { Movie } from "./models/Movie.js";
import { Series } from "./models/Series.js";
import { WatchHistory } from "./models/WatchHistory.js";
import { WatchlistItem } from "./models/WatchlistItem.js";
import { UserRating } from "./models/UserRating.js";
import { Genre } from "./models/Genre.js";
import type { MovieDocument, SeriesDocument } from "./types.js";

/**
 * Home page rails — each rail is a horizontal row of content cards.
 * Returns a structured object the frontend can render directly.
 */
async function get_home_rails(user_id?: string) {
    const [trending_movies, trending_series, top_rated_movies, top_rated_series, new_release_movies, recent_series, genres] =
        await Promise.all([
            Movie.find().sort({ popularity: -1 }).limit(10).lean(),
            Series.find().sort({ popularity: -1 }).limit(10).lean(),
            Movie.find({ vote_count: { $gte: 50 } }).sort({ vote_average: -1 }).limit(10).lean(),
            Series.find({ vote_count: { $gte: 50 } }).sort({ vote_average: -1 }).limit(10).lean(),
            Movie.find().sort({ release_date: -1 }).limit(10).lean(),
            Series.find().sort({ first_air_date: -1 }).limit(10).lean(),
            Genre.find().sort({ name: 1 }).lean()
        ]);

    const rails: Record<string, unknown>[] = [
        { id: "trending_movies", title: "Trending Movies", content_type: "movie", items: trending_movies },
        { id: "trending_series", title: "Trending TV Shows", content_type: "series", items: trending_series },
        { id: "top_rated_movies", title: "Top Rated Movies", content_type: "movie", items: top_rated_movies },
        { id: "top_rated_series", title: "Top Rated TV Shows", content_type: "series", items: top_rated_series },
        { id: "new_releases", title: "New Releases", content_type: "movie", items: new_release_movies },
        { id: "recent_series", title: "Recently Added TV Shows", content_type: "series", items: recent_series }
    ];

    // Continue watching rail (authenticated users only)
    if (user_id) {
        const continue_items = await WatchHistory.find({
            user_id,
            completed: false,
            progress_seconds: { $gt: 0 }
        })
            .sort({ last_watched_at: -1 })
            .limit(10)
            .lean();

        if (continue_items.length > 0) {
            const movie_ids = continue_items
                .filter((h) => h.content_type === "movie")
                .map((h) => h.tmdb_id);
            const series_ids = continue_items
                .filter((h) => h.content_type === "series")
                .map((h) => h.tmdb_id);

            const [movies, series_list] = await Promise.all([
                movie_ids.length > 0 ? Movie.find({ tmdb_id: { $in: movie_ids } }).lean() : [],
                series_ids.length > 0 ? Series.find({ tmdb_id: { $in: series_ids } }).lean() : []
            ]);

            const content_map = new Map<string, MovieDocument | SeriesDocument>();
            for (const m of movies) content_map.set(`movie_${m.tmdb_id}`, m as unknown as MovieDocument);
            for (const s of series_list) content_map.set(`series_${s.tmdb_id}`, s as unknown as SeriesDocument);

            const continue_watching = continue_items
                .map((h) => {
                    const content = content_map.get(`${h.content_type}_${h.tmdb_id}`);
                    if (!content) return null;
                    return {
                        ...content,
                        _history: {
                            progress_seconds: h.progress_seconds,
                            season_number: h.season_number,
                            episode_number: h.episode_number,
                            last_watched_at: h.last_watched_at
                        }
                    };
                })
                .filter((item): item is NonNullable<typeof item> => item !== null);

            rails.unshift({
                id: "continue_watching",
                title: "Continue Watching",
                content_type: "mixed",
                items: continue_watching
            });
        }
    }

    return { rails, genres };
}

/**
 * Genre-filtered browse page data.
 */
async function get_content_by_genre(genre_id: number, page: number = 1, limit: number = 20) {
    const skip = (page - 1) * limit;

    const [movies, series_list, movie_total, series_total] = await Promise.all([
        Movie.find({ "genres.genre_id": genre_id })
            .sort({ popularity: -1 })
            .skip(skip)
            .limit(limit)
            .lean(),
        Series.find({ "genres.genre_id": genre_id })
            .sort({ popularity: -1 })
            .skip(skip)
            .limit(limit)
            .lean(),
        Movie.countDocuments({ "genres.genre_id": genre_id }),
        Series.countDocuments({ "genres.genre_id": genre_id })
    ]);

    return {
        movies,
        series: series_list,
        pagination: {
            page,
            limit,
            total_movies: movie_total,
            total_series: series_total,
            has_more_movies: skip + limit < movie_total,
            has_more_series: skip + limit < series_total
        }
    };
}

/**
 * Profile statistics for an authenticated user.
 */
async function get_profile_stats(user_id: string) {
    const [
        watchlist_count,
        completed_count,
        watching_count,
        ratings_count,
        history_count,
        avg_rating
    ] = await Promise.all([
        WatchlistItem.countDocuments({ user_id }),
        WatchlistItem.countDocuments({ user_id, status: "completed" }),
        WatchlistItem.countDocuments({ user_id, status: "watching" }),
        UserRating.countDocuments({ user_id }),
        WatchHistory.countDocuments({ user_id }),
        UserRating.aggregate([
            { $match: { user_id } },
            { $group: { _id: null, avg: { $avg: "$rating" } } }
        ])
    ]);

    return {
        watchlist_count,
        completed_count,
        watching_count,
        ratings_count,
        history_count,
        average_rating: avg_rating.length > 0 ? Math.round(avg_rating[0].avg * 10) / 10 : 0
    };
}

/**
 * Recent activity feed for profile page.
 */
async function get_recent_activity(user_id: string, limit: number = 20) {
    const [recent_history, recent_ratings, recent_watchlist] = await Promise.all([
        WatchHistory.find({ user_id }).sort({ last_watched_at: -1 }).limit(limit).lean(),
        UserRating.find({ user_id }).sort({ created_at: -1 }).limit(limit).lean(),
        WatchlistItem.find({ user_id }).sort({ updated_at: -1 }).limit(limit).lean()
    ]);

    return {
        recent_history,
        recent_ratings,
        recent_watchlist
    };
}

export { get_home_rails, get_content_by_genre, get_profile_stats, get_recent_activity };
