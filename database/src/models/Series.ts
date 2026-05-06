import mongoose, { Schema, type Document } from "mongoose";
import type {
    GenreDocument,
    CastDocument,
    CrewDocument,
    SeasonDocument,
    EpisodeDocument
} from "../types.js";

export interface SeriesDoc extends Document {
    tmdb_id: number;
    name: string;
    original_name: string | null;
    tagline: string | null;
    overview: string;
    poster_path: string | null;
    backdrop_path: string | null;
    first_air_date: string | null;
    last_air_date: string | null;
    original_language: string | null;
    popularity: number;
    vote_average: number;
    vote_count: number;
    adult: boolean;
    episode_run_time: number[];
    type: string | null;
    status: string | null;
    imdb_id: string | null;
    homepage: string | null;
    number_of_seasons: number;
    number_of_episodes: number;
    genres: GenreDocument[];
    cast: CastDocument[];
    crew: CrewDocument[];
    seasons: SeasonDocument[];
    networks_json: Record<string, unknown>[];
    production_countries_json: Record<string, unknown>[];
    spoken_languages_json: Record<string, unknown>[];
    raw_data: Record<string, unknown>;
    created_at: Date;
    updated_at: Date;
}

const episode_schema = new Schema<EpisodeDocument>({
    episode_number: { type: Number, required: true },
    name: { type: String, default: "" },
    overview: { type: String, default: "" },
    still_path: { type: String, default: null },
    air_date: { type: String, default: null },
    runtime: { type: Number, default: null },
    vote_average: { type: Number, default: 0 },
    vote_count: { type: Number, default: 0 },
    season_number: { type: Number, required: true }
}, { _id: false });

const season_schema = new Schema<SeasonDocument>({
    season_number: { type: Number, required: true },
    name: { type: String, default: "" },
    overview: { type: String, default: "" },
    poster_path: { type: String, default: null },
    air_date: { type: String, default: null },
    episode_count: { type: Number, default: 0 },
    episodes: [episode_schema]
}, { _id: false });

const series_schema = new Schema<SeriesDoc>({
    tmdb_id: { type: Number, required: true, unique: true },
    name: { type: String, required: true },
    original_name: { type: String, default: null },
    tagline: { type: String, default: null },
    overview: { type: String, default: "" },
    poster_path: { type: String, default: null },
    backdrop_path: { type: String, default: null },
    first_air_date: { type: String, default: null },
    last_air_date: { type: String, default: null },
    original_language: { type: String, default: null },
    popularity: { type: Number, default: 0 },
    vote_average: { type: Number, default: 0 },
    vote_count: { type: Number, default: 0 },
    adult: { type: Boolean, default: false },
    episode_run_time: { type: [Number], default: [] },
    type: { type: String, default: null },
    status: { type: String, default: null },
    imdb_id: { type: String, default: null },
    homepage: { type: String, default: null },
    number_of_seasons: { type: Number, default: 0 },
    number_of_episodes: { type: Number, default: 0 },
    genres: [{ genre_id: Number, name: String }],
    cast: [{
        person_id: Number,
        name: String,
        profile_path: String,
        character_name: String,
        cast_order: Number
    }],
    crew: [{
        person_id: Number,
        name: String,
        profile_path: String,
        job: String
    }],
    seasons: [season_schema],
    networks_json: { type: [Object], default: [] },
    production_countries_json: { type: [Object], default: [] },
    spoken_languages_json: { type: [Object], default: [] },
    raw_data: { type: Schema.Types.Mixed, default: {} }
}, {
    timestamps: { createdAt: "created_at", updatedAt: "updated_at" }
});

series_schema.index({ "genres.genre_id": 1 });
series_schema.index({ name: "text", overview: "text" });
series_schema.index({ popularity: -1 });
series_schema.index({ vote_average: -1 });
series_schema.index({ first_air_date: -1 });

export const Series = mongoose.model<SeriesDoc>("Series", series_schema);
