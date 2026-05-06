/**
 * MongoDB Document Model — movies collection
 *
 * Single embedded document replaces the 6 MySQL tables:
 *   movies, genres, people, movie_genres, movie_cast, movie_crew
 *
 * Document structure:
 * {
 *   _id:            Number   — tmdb_id used as primary key
 *   tmdb_id:        Number   — TMDB movie ID
 *   title:          String   — movie title
 *   runtime:        Number   — minutes
 *   vote_average:   Number   — TMDB rating (0-10)
 *   overview:       String   — plot summary
 *   release_date:   String   — ISO date (YYYY-MM-DD)
 *   poster_path:    String   — TMDB poster path
 *   genres:         Array    — embedded genre objects
 *     { genre_id: Number, name: String }
 *   cast:           Array    — top 5 actors (embedded)
 *     { person_id: Number, name: String, profile_path: String, character_name: String, cast_order: Number }
 *   crew:           Array    — directors (embedded)
 *     { person_id: Number, name: String, profile_path: String, job: String }
 *   raw_data:       Object   — full TMDB API response
 *   created_at:     Date     — document creation timestamp
 *   updated_at:     Date     — last update timestamp
 * }
 *
 * Indexes (created in db.js):
 *   { tmdb_id: 1 }           — unique
 *   { "genres.genre_id": 1 } — genre filtering
 *   { title: "text" }        — text search
 */

// Example document for reference:
const example_movie = {
    _id: 550,
    tmdb_id: 550,
    title: "Fight Club",
    runtime: 139,
    vote_average: 8.4,
    overview: "A ticking-Loss-bomb insomniac and a slippery soap salesman build a global organization to help vent male aggression.",
    release_date: "1999-10-15",
    poster_path: "/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg",
    genres: [
        { genre_id: 18, name: "Drama" },
        { genre_id: 53, name: "Thriller" }
    ],
    cast: [
        { person_id: 819, name: "Edward Norton", profile_path: "/8nytsqL59SFJTVYVrN72tmO6DDW.jpg", character_name: "The Narrator", cast_order: 0 },
        { person_id: 287, name: "Brad Pitt", profile_path: "/cckcYc2v0yh1tc9QjRelptcOBko.jpg", character_name: "Tyler Durden", cast_order: 1 }
    ],
    crew: [
        { person_id: 7467, name: "David Fincher", profile_path: "/dcVWmM巴菲.jpg", job: "Director" }
    ],
    raw_data: { /* full TMDB /movie/{id}?append_to_response=credits response */ },
    created_at: "2026-05-06T00:00:00.000Z",
    updated_at: "2026-05-06T00:00:00.000Z"
};

module.exports = { example_movie };
