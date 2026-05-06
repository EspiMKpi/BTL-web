import mongoose, { Schema, type Document } from "mongoose";
import type { GenreDocument, CastDocument, CrewDocument } from "../types.js";

export interface MovieDoc extends Document {
    tmdb_id: number;
    title: string;
    runtime: number | null;
    vote_average: number;
    overview: string;
    release_date: string | null;
    poster_path: string | null;
    genres: GenreDocument[];
    cast: CastDocument[];
    crew: CrewDocument[];
    raw_data: Record<string, unknown>;
    created_at: Date;
    updated_at: Date;
}

const movie_schema = new Schema<MovieDoc>({
    tmdb_id: { type: Number, required: true, unique: true },
    title: { type: String, required: true },
    runtime: { type: Number, default: null },
    vote_average: { type: Number, default: 0 },
    overview: { type: String, default: "" },
    release_date: { type: String, default: null },
    poster_path: { type: String, default: null },
    genres: [{ genre_id: Number, name: String }],
    cast: [{ person_id: Number, name: String, profile_path: String, character_name: String, cast_order: Number }],
    crew: [{ person_id: Number, name: String, profile_path: String, job: String }],
    raw_data: { type: Schema.Types.Mixed, default: {} }
}, {
    timestamps: { createdAt: "created_at", updatedAt: "updated_at" }
});

movie_schema.index({ "genres.genre_id": 1 });
movie_schema.index({ title: "text" });

export const Movie = mongoose.model<MovieDoc>("Movie", movie_schema);
