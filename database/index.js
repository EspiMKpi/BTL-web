const express = require("express");
const path = require("path");
const { connect_mongo } = require("./db");
const { get_movie_by_id } = require("./movieService");

const app = express();
const PORT = 3000;

// Serve frontend static files from project root
app.use(express.static(path.join(__dirname, "..")));

app.get("/movie/:id", async (req, res) => {
    try {
        const movie = await get_movie_by_id(parseInt(req.params.id));
        res.json(movie);
    } catch (error) {
        res.status(404).json({ error: error.message });
    }
});

// Start server after MongoDB connects
connect_mongo().then(() => {
    app.listen(PORT, () => {
        console.log(`Server is running on http://localhost:${PORT}`);
    });
});