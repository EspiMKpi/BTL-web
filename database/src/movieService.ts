import axios from "axios";
import { Movie } from "./models/Movie.js";
import { Genre } from "./models/Genre.js";
import type { MovieDocument, TmdbMovieResponse } from "./types.js";

/**
 * Fetch a movie by TMDB ID. Checks MongoDB first, then falls back to TMDB API.
 * Upserts the full ERD-driven document including all fields.
 */
async function get_movie_by_id(tmdb_id: number): Promise<MovieDocument> {
    try {
        const existing_doc = await Movie.findOne({ tmdb_id }).lean();
        if (existing_doc && existing_doc.raw_data && existing_doc.title) {
            console.log(`Movie ${tmdb_id} served from MongoDB`);
            return existing_doc as unknown as MovieDocument;
        }

        console.log(`Movie ${tmdb_id} fetching from TMDB...`);
        const response = await axios.get<TmdbMovieResponse>(
            `https://api.themoviedb.org/3/movie/${tmdb_id}?api_key=${process.env.TMDB_API_KEY}&append_to_response=credits`
        );
        const data = response.data;

        // Upsert genres into the genres collection
        for (const genre of data.genres || []) {
            await Genre.updateOne(
                { genre_id: genre.id },
                { $set: { name: genre.name } },
                { upsert: true }
            );
        }

        const movie_document: Partial<MovieDocument> = {
            tmdb_id: data.id,
            title: data.title,
            original_title: data.original_title || null,
            tagline: data.tagline || null,
            overview: data.overview || "",
            poster_path: data.poster_path || null,
            backdrop_path: data.backdrop_path || null,
            release_date: data.release_date || null,
            original_language: data.original_language || null,
            popularity: data.popularity || 0,
            vote_average: data.vote_average || 0,
            vote_count: data.vote_count || 0,
            adult: data.adult || false,
            video: data.video || false,
            runtime: data.runtime ?? null,
            budget: data.budget || 0,
            revenue: data.revenue || 0,
            status: data.status || null,
            imdb_id: data.imdb_id || null,
            homepage: data.homepage || null,
            genres: (data.genres || []).map((g) => ({
                genre_id: g.id,
                name: g.name
            })),
            cast: (data.credits?.cast || []).slice(0, 20).map((a) => ({
                person_id: a.id,
                name: a.name,
                profile_path: a.profile_path,
                character_name: a.character,
                cast_order: a.order
            })),
            crew: (data.credits?.crew || [])
                .filter((m) => ["Director", "Producer", "Writer"].includes(m.job))
                .slice(0, 10)
                .map((c) => ({
                    person_id: c.id,
                    name: c.name,
                    profile_path: c.profile_path,
                    job: c.job
                })),
            production_countries_json: (data.production_countries || []) as unknown as Record<string, unknown>[],
            spoken_languages_json: (data.spoken_languages || []) as unknown as Record<string, unknown>[],
            raw_data: data as unknown as Record<string, unknown>,
            updated_at: new Date()
        };

        const result = await Movie.findOneAndUpdate(
            { tmdb_id: data.id },
            {
                $set: movie_document,
                $setOnInsert: { created_at: new Date() }
            },
            { upsert: true, returnDocument: 'after', lean: true }
        );

        return result as unknown as MovieDocument;
    } catch (error) {
        console.error(`Failed to fetch movie ${tmdb_id}:`, error);
        throw new Error("Failed to fetch movie");
    }
}

/**
 * Get multiple movies by tmdb_ids (for rails / collections).
 */
async function get_movies_by_ids(tmdb_ids: number[]): Promise<MovieDocument[]> {
    const docs = await Movie.find({ tmdb_id: { $in: tmdb_ids } }).lean();
    return docs as unknown as MovieDocument[];
}

/**
 * Search movies stored in MongoDB by title substring.
 */
async function search_movies(query: string, limit: number = 20): Promise<MovieDocument[]> {
    const docs = await Movie.find(
        { $text: { $search: query } },
        { score: { $meta: "textScore" } }
    )
        .sort({ score: { $meta: "textScore" } })
        .limit(limit)
        .lean();
    return docs as unknown as MovieDocument[];
}

export { get_movie_by_id, get_movies_by_ids, search_movies };
