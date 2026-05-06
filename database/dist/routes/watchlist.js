import { Router } from "express";
import { WatchlistItem } from "../models/WatchlistItem.js";
import { auth_middleware } from "../middleware/auth.js";
const router = Router();
// All watchlist routes require authentication
router.use(auth_middleware);
// GET /api/watchlist — get current user's watchlist
router.get("/", async (req, res) => {
    try {
        const user_id = req.user.user_id;
        const { status, content_type } = req.query;
        const filter = { user_id };
        if (status)
            filter.status = status;
        if (content_type)
            filter.content_type = content_type;
        const items = await WatchlistItem.find(filter)
            .sort({ updated_at: -1 })
            .lean();
        res.json(items);
    }
    catch (error) {
        res.status(500).json({ error: error.message });
    }
});
// POST /api/watchlist — add item to watchlist
router.post("/", async (req, res) => {
    try {
        const user_id = req.user.user_id;
        const { content_type, tmdb_id, status, is_bookmarked } = req.body;
        if (!content_type || !tmdb_id) {
            res.status(400).json({ error: "content_type and tmdb_id are required" });
            return;
        }
        const item = await WatchlistItem.findOneAndUpdate({ user_id, content_type, tmdb_id }, {
            $setOnInsert: { user_id, content_type, tmdb_id, created_at: new Date() },
            $set: {
                status: status || "plan_to_watch",
                is_bookmarked: is_bookmarked ?? true,
                updated_at: new Date()
            }
        }, { upsert: true, new: true });
        res.status(201).json(item);
    }
    catch (error) {
        res.status(500).json({ error: error.message });
    }
});
// PATCH /api/watchlist/:itemId — update watchlist item
router.patch("/:itemId", async (req, res) => {
    try {
        const user_id = req.user.user_id;
        const { itemId } = req.params;
        const updates = req.body;
        // Only allow updating own watchlist items
        const item = await WatchlistItem.findOneAndUpdate({ _id: itemId, user_id }, { $set: { ...updates, updated_at: new Date() } }, { new: true });
        if (!item) {
            res.status(404).json({ error: "Watchlist item not found" });
            return;
        }
        res.json(item);
    }
    catch (error) {
        res.status(500).json({ error: error.message });
    }
});
// DELETE /api/watchlist/:itemId — remove from watchlist
router.delete("/:itemId", async (req, res) => {
    try {
        const user_id = req.user.user_id;
        const { itemId } = req.params;
        const item = await WatchlistItem.findOneAndDelete({ _id: itemId, user_id });
        if (!item) {
            res.status(404).json({ error: "Watchlist item not found" });
            return;
        }
        res.json({ message: "Removed from watchlist" });
    }
    catch (error) {
        res.status(500).json({ error: error.message });
    }
});
export default router;
//# sourceMappingURL=watchlist.js.map