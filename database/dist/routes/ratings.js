import { Router } from "express";
import { UserRating } from "../models/UserRating.js";
import { WatchlistItem } from "../models/WatchlistItem.js";
import { auth_middleware } from "../middleware/auth.js";
const router = Router();
// GET /api/ratings — public: get ratings for a content item
router.get("/", async (req, res) => {
    try {
        const { tmdb_id, content_type } = req.query;
        if (!tmdb_id) {
            res.status(400).json({ error: "tmdb_id is required" });
            return;
        }
        const filter = { tmdb_id: Number(tmdb_id) };
        if (content_type)
            filter.content_type = content_type;
        const ratings = await UserRating.find(filter)
            .sort({ created_at: -1 })
            .limit(50)
            .lean();
        // Compute aggregate stats
        const stats = await UserRating.aggregate([
            { $match: filter },
            {
                $group: {
                    _id: null,
                    avg_rating: { $avg: "$rating" },
                    total_ratings: { $sum: 1 }
                }
            }
        ]);
        res.json({
            ratings,
            stats: stats.length > 0
                ? {
                    average: Math.round(stats[0].avg_rating * 10) / 10,
                    count: stats[0].total_ratings
                }
                : { average: 0, count: 0 }
        });
    }
    catch (error) {
        res.status(500).json({ error: error.message });
    }
});
// GET /api/ratings/me — get current user's ratings
router.get("/me", auth_middleware, async (req, res) => {
    try {
        const user_id = req.user.user_id;
        const { content_type } = req.query;
        const filter = { user_id };
        if (content_type)
            filter.content_type = content_type;
        const ratings = await UserRating.find(filter)
            .sort({ created_at: -1 })
            .lean();
        res.json(ratings);
    }
    catch (error) {
        res.status(500).json({ error: error.message });
    }
});
// POST /api/ratings — create or update a rating (authenticated)
router.post("/", auth_middleware, async (req, res) => {
    try {
        const user_id = req.user.user_id;
        const { content_type, tmdb_id, rating, review } = req.body;
        if (!content_type || !tmdb_id || rating === undefined) {
            res.status(400).json({ error: "content_type, tmdb_id, and rating are required" });
            return;
        }
        if (rating < 0 || rating > 10) {
            res.status(400).json({ error: "Rating must be between 0 and 10" });
            return;
        }
        const user_rating = await UserRating.findOneAndUpdate({ user_id, content_type, tmdb_id }, {
            $set: { rating, review: review || null, updated_at: new Date() },
            $setOnInsert: { user_id, content_type, tmdb_id, created_at: new Date() }
        }, { upsert: true, new: true });
        // Also update the watchlist item rating if it exists
        await WatchlistItem.updateOne({ user_id, content_type, tmdb_id }, { $set: { rating, updated_at: new Date() } });
        res.status(201).json(user_rating);
    }
    catch (error) {
        res.status(500).json({ error: error.message });
    }
});
// DELETE /api/ratings — remove user's rating
router.delete("/", auth_middleware, async (req, res) => {
    try {
        const user_id = req.user.user_id;
        const { content_type, tmdb_id } = req.body;
        if (!content_type || !tmdb_id) {
            res.status(400).json({ error: "content_type and tmdb_id are required" });
            return;
        }
        await UserRating.findOneAndDelete({ user_id, content_type, tmdb_id });
        res.json({ message: "Rating removed" });
    }
    catch (error) {
        res.status(500).json({ error: error.message });
    }
});
export default router;
//# sourceMappingURL=ratings.js.map