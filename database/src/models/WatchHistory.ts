import mongoose, { Schema, type Document } from "mongoose";
import type { WatchHistoryDocument } from "../types.js";

export interface WatchHistoryDoc extends Document, WatchHistoryDocument {}

const watch_history_schema = new Schema<WatchHistoryDoc>({
    user_id: { type: String, required: true, index: true },
    content_type: { type: String, required: true, enum: ["movie", "series"] },
    tmdb_id: { type: Number, required: true },
    season_number: { type: Number, default: null },
    episode_number: { type: Number, default: null },
    progress_seconds: { type: Number, default: 0 },
    completed: { type: Boolean, default: false },
    last_watched_at: { type: Date, default: () => new Date() }
}, {
    timestamps: { createdAt: "created_at", updatedAt: false }
});

// Compound index: one history entry per user per content per episode
watch_history_schema.index(
    { user_id: 1, content_type: 1, tmdb_id: 1, season_number: 1, episode_number: 1 },
    { unique: true }
);
watch_history_schema.index({ user_id: 1, last_watched_at: -1 });
watch_history_schema.index({ user_id: 1, completed: 1 });

export const WatchHistory = mongoose.model<WatchHistoryDoc>("WatchHistory", watch_history_schema);
