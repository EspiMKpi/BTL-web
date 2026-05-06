import mongoose, { type Document } from "mongoose";
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
export declare const Movie: mongoose.Model<MovieDoc, {}, {}, {}, mongoose.Document<unknown, {}, MovieDoc, {}, mongoose.DefaultSchemaOptions> & MovieDoc & Required<{
    _id: mongoose.Types.ObjectId;
}> & {
    __v: number;
} & {
    id: string;
}, any, MovieDoc>;
//# sourceMappingURL=Movie.d.ts.map