import { Router, type Request, type Response } from "express";
import { WatchHistory } from "../models/WatchHistory.js";
import { auth_middleware } from "../middleware/auth.js";

const router = Router();

// All history routes require authentication
router.use(auth_middleware);

// GET /api/history/continue-watching — get items with progress for continue watching rail
router.get("/continue-watching", async (req: Request, res: Response) => {
    try {
        const user_id = req.user!.user_id;

        const items = await WatchHistory.find({
            user_id,
            completed: false,
            progress_seconds: { $gt: 0 }
        })
            .sort({ last_watched_at: -1 })
            .limit(20)
            .lean();

        res.json(items);
    } catch (error) {
        res.status(500).json({ error: (error as Error).message });
    }
});

// GET /api/history — get full watch history
router.get("/", async (req: Request, res: Response) => {
    try {
        const user_id = req.user!.user_id;
        const { content_type } = req.query;

        const filter: Record<string, unknown> = { user_id };
        if (content_type) filter.content_type = content_type;

        const items = await WatchHistory.find(filter)
            .sort({ last_watched_at: -1 })
            .limit(50)
            .lean();

        res.json(items);
    } catch (error) {
        res.status(500).json({ error: (error as Error).message });
    }
});

// POST /api/history/progress — update watch progress
router.post("/progress", async (req: Request, res: Response) => {
    try {
        const user_id = req.user!.user_id;
        const {
            content_type,
            tmdb_id,
            season_number,
            episode_number,
            progress_seconds,
            completed
        } = req.body;

        if (!content_type || !tmdb_id) {
            res.status(400).json({ error: "content_type and tmdb_id are required" });
            return;
        }

        const item = await WatchHistory.findOneAndUpdate(
            {
                user_id,
                content_type,
                tmdb_id,
                season_number: season_number ?? null,
                episode_number: episode_number ?? null
            },
            {
                $set: {
                    progress_seconds: progress_seconds || 0,
                    completed: completed || false,
                    last_watched_at: new Date()
                },
                $setOnInsert: {
                    user_id,
                    content_type,
                    tmdb_id,
                    season_number: season_number ?? null,
                    episode_number: episode_number ?? null,
                    created_at: new Date()
                }
            },
            { upsert: true, new: true }
        );

        res.json(item);
    } catch (error) {
        res.status(500).json({ error: (error as Error).message });
    }
});

export default router;
