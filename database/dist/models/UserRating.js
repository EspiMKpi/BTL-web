import mongoose, { Schema } from "mongoose";
const user_rating_schema = new Schema({
    user_id: { type: String, required: true, index: true },
    content_type: { type: String, required: true, enum: ["movie", "series"] },
    tmdb_id: { type: Number, required: true },
    rating: { type: Number, required: true, min: 0, max: 10 },
    review: { type: String, default: null }
}, {
    timestamps: { createdAt: "created_at", updatedAt: "updated_at" }
});
// One rating per user per content
user_rating_schema.index({ user_id: 1, content_type: 1, tmdb_id: 1 }, { unique: true });
user_rating_schema.index({ user_id: 1, created_at: -1 });
user_rating_schema.index({ tmdb_id: 1, content_type: 1 });
export const UserRating = mongoose.model("UserRating", user_rating_schema);
//# sourceMappingURL=UserRating.js.map