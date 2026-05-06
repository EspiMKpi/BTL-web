import { Router, type Request, type Response } from "express";
import { get_movie_by_id } from "../movieService.js";
import { get_series_by_id } from "../seriesService.js";
import { get_home_rails, get_content_by_genre } from "../libraryService.js";
import { Genre } from "../models/Genre.js";
import { optional_auth } from "../middleware/auth.js";

const router = Router();

// GET /api/content/home — Netflix-style home page rails
// Uses optional auth so Continue Watching rail appears for logged-in users
router.get("/home", optional_auth, async (req: Request, res: Response) => {
    try {
        const user_id = req.user?.user_id;
        const data = await get_home_rails(user_id);
        res.json(data);
    } catch (error) {
        res.status(500).json({ error: (error as Error).message });
    }
});

// GET /api/content/genres — list all genres
router.get("/genres", async (_req: Request, res: Response) => {
    try {
        const genres = await Genre.find().sort({ name: 1 }).lean();
        res.json(genres);
    } catch (error) {
        res.status(500).json({ error: (error as Error).message });
    }
});

// GET /api/content/browse/:genre_id — browse content by genre
router.get("/browse/:genre_id", async (req: Request, res: Response) => {
    try {
        const genre_id = Number(req.params.genre_id);
        const page = req.query.page ? Number(req.query.page) : 1;
        const limit = req.query.limit ? Number(req.query.limit) : 20;
        const data = await get_content_by_genre(genre_id, page, limit);
        res.json(data);
    } catch (error) {
        res.status(500).json({ error: (error as Error).message });
    }
});

// GET /api/content/movie/:id — get movie details
router.get("/movie/:id", async (req: Request, res: Response) => {
    try {
        const id = Array.isArray(req.params.id) ? req.params.id[0] : req.params.id;
        const movie = await get_movie_by_id(parseInt(id));
        res.json(movie);
    } catch (error) {
        res.status(404).json({ error: (error as Error).message });
    }
});

// GET /api/content/series/:id — get series details with seasons/episodes
router.get("/series/:id", async (req: Request, res: Response) => {
    try {
        const id = Array.isArray(req.params.id) ? req.params.id[0] : req.params.id;
        const series = await get_series_by_id(parseInt(id));
        res.json(series);
    } catch (error) {
        res.status(404).json({ error: (error as Error).message });
    }
});

export default router;
