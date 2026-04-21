const axios = require('axios');
const { pool, redisClient } = require('./db');

async function getMovieById(tmdbId) {
    const redisKey = `movie:full:${tmdbId}`;

    try {
        // 1. Check Redis
        const cachedMovie = await redisClient.get(redisKey);
        if (cachedMovie) {
            console.log("Serving from Redis");
            return JSON.parse(cachedMovie);
        }

        // 2. Check MySQL
        const [rows] = await pool.execute("SELECT raw_data FROM movies WHERE tmdb_id = ?", [tmdbId]);
        if (rows.length > 0 && rows[0].raw_data) {
            console.log("Serving from MySQL");
            const movieData = rows[0].raw_data;
            await redisClient.setEx(redisKey, 3600, JSON.stringify(movieData));
            return movieData;
        }

        // 3. Fetch from TMDB
        console.log("Fetching everything from TMDB...");
           const response = await axios.get(
             `https://api.themoviedb.org/3/movie/${tmdbId}?api_key=${process.env.TMDB_API_KEY}&append_to_response=credits`
        );
           const data = response.data;

        await pool.execute(
            `INSERT INTO movies (tmdb_id, title, runtime, vote_average, overview, release_date, poster_path, raw_data) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON DUPLICATE KEY UPDATE title=VALUES(title)`,
            [data.id, data.title, data.runtime, data.vote_average, data.overview, data.release_date || null, data.poster_path, JSON.stringify(data)]
        );

        for (const genre of data.genres){
            await pool.execute("INSERT IGNORE INTO genres (id, name) VALUES (?, ?)", [genre.id, genre.name]);
            await pool.execute("INSERT IGNORE INTO movie_genres (movie_id, genre_id) VALUES (?, ?)", [data.id, genre.id]);
        }

        const directors = data.credits.crew.filter(member => member.job === 'Director');
        for (const dir of directors){
            await pool.execute("INSERT IGNORE INTO people (id, name, profile_path) VALUES (?, ?, ?)", [dir.id, dir.name, dir.profile_path]);
            await pool.execute("INSERT IGNORE INTO movie_crew (movie_id, person_id, job) VALUES (?, ?, ?)", [data.id, dir.id, 'Director']);
        }

        const topActors = data.credits.cast.slice(0, 5);
        for (const actor of topActors) {
            await pool.execute("INSERT IGNORE INTO people (id, name, profile_path) VALUES (?, ?, ?)", [actor.id, actor.name, actor.profile_path]);
            await pool.execute("INSERT IGNORE INTO movie_cast (movie_id, person_id, character_name, cast_order) VALUES (?, ?, ?, ?)", 
                [data.id, actor.id, actor.character, actor.order]);
        }

        return data;
    } catch (error) {
        console.error(error);
        throw new Error("Failed to fetch movie");
    }
}

module.exports = { getMovieById };