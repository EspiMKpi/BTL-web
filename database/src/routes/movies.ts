import { Router, type Request, type Response } from "express";
import { get_movie_by_id } from "../movieService.js";

const router = Router();

router.get("/:id", async (req: Request, res: Response) => {
    try {
        const id = Array.isArray(req.params.id) ? req.params.id[0] : req.params.id;
        const movie = await get_movie_by_id(parseInt(id));
        res.json(movie);
    } catch (error) {
        res.status(404).json({ error: (error as Error).message });
    }
});

export default router;
