import { Router } from "express";
import { auth_middleware } from "../middleware/auth.js";
import { User } from "../models/User.js";
import { get_profile_stats, get_recent_activity } from "../libraryService.js";
const router = Router();
// All profile routes require authentication
router.use(auth_middleware);
// GET /api/profile/stats — get user's viewing statistics
router.get("/stats", async (req, res) => {
    try {
        const user_id = req.user.user_id;
        const stats = await get_profile_stats(user_id);
        res.json(stats);
    }
    catch (error) {
        res.status(500).json({ error: error.message });
    }
});
// GET /api/profile/recent-activity — get user's recent activity feed
router.get("/recent-activity", async (req, res) => {
    try {
        const user_id = req.user.user_id;
        const limit = req.query.limit ? Number(req.query.limit) : 20;
        const activity = await get_recent_activity(user_id, limit);
        res.json(activity);
    }
    catch (error) {
        res.status(500).json({ error: error.message });
    }
});
// GET /api/profile — get user profile
router.get("/", async (req, res) => {
    try {
        const user = await User.findById(req.user.user_id);
        if (!user) {
            res.status(404).json({ error: "User not found" });
            return;
        }
        res.json({
            id: user._id,
            email: user.email,
            username: user.username,
            avatar_url: user.avatar_url,
            role: user.role,
            is_active: user.is_active,
            created_at: user.created_at
        });
    }
    catch (error) {
        res.status(500).json({ error: error.message });
    }
});
// PATCH /api/profile — update user profile
router.patch("/", async (req, res) => {
    try {
        const user_id = req.user.user_id;
        const { username, avatar_url } = req.body;
        const updates = {};
        if (username !== undefined)
            updates.username = username;
        if (avatar_url !== undefined)
            updates.avatar_url = avatar_url;
        if (Object.keys(updates).length === 0) {
            res.status(400).json({ error: "No fields to update" });
            return;
        }
        const user = await User.findByIdAndUpdate(user_id, { $set: updates }, { new: true });
        if (!user) {
            res.status(404).json({ error: "User not found" });
            return;
        }
        res.json({
            id: user._id,
            email: user.email,
            username: user.username,
            avatar_url: user.avatar_url,
            role: user.role
        });
    }
    catch (error) {
        res.status(500).json({ error: error.message });
    }
});
export default router;
//# sourceMappingURL=profile.js.map