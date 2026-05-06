import mongoose, { Schema } from "mongoose";
const movie_schema = new Schema({
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
export const Movie = mongoose.model("Movie", movie_schema);
//# sourceMappingURL=Movie.js.map