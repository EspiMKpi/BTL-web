import mongoose, { Schema } from "mongoose";
const watchlist_item_schema = new Schema({
    user_id: { type: String, required: true, index: true },
    content_type: { type: String, required: true, enum: ["movie", "series"] },
    tmdb_id: { type: Number, required: true },
    status: {
        type: String,
        required: true,
        enum: ["plan_to_watch", "watching", "completed", "dropped"],
        default: "plan_to_watch"
    },
    progress_seconds: { type: Number, default: 0 },
    current_season: { type: Number, default: null },
    current_episode: { type: Number, default: null },
    rating: { type: Number, default: null, min: 0, max: 10 },
    review: { type: String, default: null },
    is_bookmarked: { type: Boolean, default: false }
}, {
    timestamps: { createdAt: "created_at", updatedAt: "updated_at" }
});
// One watchlist entry per user per content
watchlist_item_schema.index({ user_id: 1, content_type: 1, tmdb_id: 1 }, { unique: true });
watchlist_item_schema.index({ user_id: 1, status: 1 });
watchlist_item_schema.index({ user_id: 1, is_bookmarked: 1 });
watchlist_item_schema.index({ user_id: 1, updated_at: -1 });
export const WatchlistItem = mongoose.model("WatchlistItem", watchlist_item_schema);
//# sourceMappingURL=WatchlistItem.js.map