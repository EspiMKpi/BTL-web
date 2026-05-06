import axios from "axios";
import { Series } from "./models/Series.js";
import { Genre } from "./models/Genre.js";
import type { SeriesDocument, TmdbSeriesResponse, TmdbSeason } from "./types.js";

/**
 * Fetch a TV series by TMDB ID. Checks MongoDB first, then falls back to TMDB API.
 * Upserts the full ERD-driven document with embedded seasons and episodes.
 */
async function get_series_by_id(tmdb_id: number): Promise<SeriesDocument> {
    try {
        const existing_doc = await Series.findOne({ tmdb_id }).lean();
        if (existing_doc && existing_doc.raw_data && existing_doc.seasons?.length > 0) {
            console.log(`Series ${tmdb_id} served from MongoDB`);
            return existing_doc as unknown as SeriesDocument;
        }

        console.log(`Series ${tmdb_id} fetching from TMDB...`);
        const response = await axios.get<TmdbSeriesResponse>(
            `https://api.themoviedb.org/3/tv/${tmdb_id}?api_key=${process.env.TMDB_API_KEY}&append_to_response=credits`
        );
        const data = response.data;

        // Upsert genres
        for (const genre of data.genres || []) {
            await Genre.updateOne(
                { genre_id: genre.id },
                { $set: { name: genre.name } },
                { upsert: true }
            );
        }

        // Fetch season details with episodes (limit to first 10 seasons to avoid rate limits)
        const seasons_to_fetch = (data.seasons || []).slice(0, 10);
        const enriched_seasons = [];

        for (const season of seasons_to_fetch) {
            try {
                const season_response = await axios.get<TmdbSeason>(
                    `https://api.themoviedb.org/3/tv/${tmdb_id}/season/${season.season_number}?api_key=${process.env.TMDB_API_KEY}`
                );
                const season_data = season_response.data;

                enriched_seasons.push({
                    season_number: season.season_number,
                    name: season.name || season_data.name || "",
                    overview: season.overview || season_data.overview || "",
                    poster_path: season.poster_path || season_data.poster_path || null,
                    air_date: season.air_date || season_data.air_date || null,
                    episode_count: season.episode_count || season_data.episodes?.length || 0,
                    episodes: (season_data.episodes || []).map((ep) => ({
                        episode_number: ep.episode_number,
                        name: ep.name || "",
                        overview: ep.overview || "",
                        still_path: ep.still_path || null,
                        air_date: ep.air_date || null,
                        runtime: ep.runtime ?? null,
                        vote_average: ep.vote_average || 0,
                        vote_count: ep.vote_count || 0,
                        season_number: ep.season_number
                    }))
                });
            } catch (season_err) {
                console.warn(`Failed to fetch season ${season.season_number} for series ${tmdb_id}, using basic info`);
                enriched_seasons.push({
                    season_number: season.season_number,
                    name: season.name || "",
                    overview: season.overview || "",
                    poster_path: season.poster_path || null,
                    air_date: season.air_date || null,
                    episode_count: season.episode_count || 0,
                    episodes: []
                });
            }
        }

        const series_document: Partial<SeriesDocument> = {
            tmdb_id: data.id,
            name: data.name,
            original_name: data.original_name || null,
            tagline: data.tagline || null,
            overview: data.overview || "",
            poster_path: data.poster_path || null,
            backdrop_path: data.backdrop_path || null,
            first_air_date: data.first_air_date || null,
            last_air_date: data.last_air_date || null,
            original_language: data.original_language || null,
            popularity: data.popularity || 0,
            vote_average: data.vote_average || 0,
            vote_count: data.vote_count || 0,
            adult: data.adult || false,
            episode_run_time: data.episode_run_time || [],
            type: data.type || null,
            status: data.status || null,
            imdb_id: data.imdb_id || null,
            homepage: data.homepage || null,
            number_of_seasons: data.number_of_seasons || 0,
            number_of_episodes: data.number_of_episodes || 0,
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
                .filter((m) => ["Director", "Producer", "Writer", "Executive Producer"].includes(m.job))
                .slice(0, 10)
                .map((c) => ({
                    person_id: c.id,
                    name: c.name,
                    profile_path: c.profile_path,
                    job: c.job
                })),
            seasons: enriched_seasons,
            networks_json: (data.networks || []) as unknown as Record<string, unknown>[],
            production_countries_json: (data.production_countries || []) as unknown as Record<string, unknown>[],
            spoken_languages_json: (data.spoken_languages || []) as unknown as Record<string, unknown>[],
            raw_data: data as unknown as Record<string, unknown>,
            updated_at: new Date()
        };

        const result = await Series.findOneAndUpdate(
            { tmdb_id: data.id },
            {
                $set: series_document,
                $setOnInsert: { created_at: new Date() }
            },
            { upsert: true, returnDocument: 'after', lean: true }
        );

        return result as unknown as SeriesDocument;
    } catch (error) {
        console.error(`Failed to fetch series ${tmdb_id}:`, error);
        throw new Error("Failed to fetch series");
    }
}

/**
 * Get multiple series by tmdb_ids (for rails / collections).
 */
async function get_series_by_ids(tmdb_ids: number[]): Promise<SeriesDocument[]> {
    const docs = await Series.find({ tmdb_id: { $in: tmdb_ids } }).lean();
    return docs as unknown as SeriesDocument[];
}

/**
 * Search series stored in MongoDB by name substring.
 */
async function search_series(query: string, limit: number = 20): Promise<SeriesDocument[]> {
    const docs = await Series.find(
        { $text: { $search: query } },
        { score: { $meta: "textScore" } }
    )
        .sort({ score: { $meta: "textScore" } })
        .limit(limit)
        .lean();
    return docs as unknown as SeriesDocument[];
}

export { get_series_by_id, get_series_by_ids, search_series };
