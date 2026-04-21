const express = require('express');
const { getMovieById } = require('./movieService');

const app = express();
const PORT = 3000;

app.get('/movie/:id', async (req, res) => {
    try {
        const movie = await getMovieById(parseInt(req.params.id));
        res.json(movie);
    } catch (error) {
        res.status(404).json({ error: error.message });
    }
});

app.listen(PORT, () => {
    console.log(`Server is running on http://localhost:${PORT}`);
});