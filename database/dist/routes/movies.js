import { Router } from "express";
import { get_movie_by_id } from "../movieService.js";
const router = Router();
router.get("/:id", async (req, res) => {
    try {
        const id = Array.isArray(req.params.id) ? req.params.id[0] : req.params.id;
        const movie = await get_movie_by_id(parseInt(id));
        res.json(movie);
    }
    catch (error) {
        res.status(404).json({ error: error.message });
    }
});
export default router;
//# sourceMappingURL=movies.js.map