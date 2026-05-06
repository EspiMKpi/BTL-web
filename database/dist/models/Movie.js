import mongoose, { Schema } from "mongoose";
const movie_schema = new Schema({
    tmdb_id: { type: Number, required: true, unique: true },
    title: { type: String, required: true },
    original_title: { type: String, default: null },
    tagline: { type: String, default: null },
    overview: { type: String, default: "" },
    poster_path: { type: String, default: null },
    backdrop_path: { type: String, default: null },
    release_date: { type: String, default: null },
    original_language: { type: String, default: null },
    popularity: { type: Number, default: 0 },
    vote_average: { type: Number, default: 0 },
    vote_count: { type: Number, default: 0 },
    adult: { type: Boolean, default: false },
    video: { type: Boolean, default: false },
    runtime: { type: Number, default: null },
    budget: { type: Number, default: 0 },
    revenue: { type: Number, default: 0 },
    status: { type: String, default: null },
    imdb_id: { type: String, default: null },
    homepage: { type: String, default: null },
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
    production_countries_json: { type: [Object], default: [] },
    spoken_languages_json: { type: [Object], default: [] },
    raw_data: { type: Schema.Types.Mixed, default: {} }
}, {
    timestamps: { createdAt: "created_at", updatedAt: "updated_at" }
});
movie_schema.index({ "genres.genre_id": 1 });
movie_schema.index({ title: "text", overview: "text" });
movie_schema.index({ popularity: -1 });
movie_schema.index({ vote_average: -1 });
movie_schema.index({ release_date: -1 });
export const Movie = mongoose.model("Movie", movie_schema);
//# sourceMappingURL=Movie.js.map