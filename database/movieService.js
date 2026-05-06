const axios = require("axios");
const { get_movies_collection } = require("./db");

async function get_movie_by_id(tmdb_id) {
    const movies_collection = get_movies_collection();

    try {
        // 1. Check MongoDB
        const existing_doc = await movies_collection.findOne({ tmdb_id: tmdb_id });
        if (existing_doc && existing_doc.raw_data) {
            console.log("Serving from MongoDB");
            return existing_doc.raw_data;
        }

        // 3. Fetch from TMDB
        console.log("Fetching everything from TMDB...");
        const response = await axios.get(
            `https://api.themoviedb.org/3/movie/${tmdb_id}?api_key=${process.env.TMDB_API_KEY}&append_to_response=credits`
        );
        const data = response.data;

        // Build embedded document from TMDB response
        const movie_document = {
            tmdb_id: data.id,
            title: data.title,
            runtime: data.runtime,
            vote_average: data.vote_average,
            overview: data.overview,
            release_date: data.release_date || null,
            poster_path: data.poster_path,
            genres: (data.genres || []).map((genre) => ({
                genre_id: genre.id,
                name: genre.name
            })),
            cast: (data.credits?.cast || []).slice(0, 5).map((actor) => ({
                person_id: actor.id,
                name: actor.name,
                profile_path: actor.profile_path,
                character_name: actor.character,
                cast_order: actor.order
            })),
            crew: (data.credits?.crew || [])
                .filter((member) => member.job === "Director")
                .map((dir) => ({
                    person_id: dir.id,
                    name: dir.name,
                    profile_path: dir.profile_path,
                    job: dir.job
                })),
            raw_data: data,
            updated_at: new Date()
        };

        // Single upsert replaces all 6 MySQL INSERT statements
        await movies_collection.updateOne(
            { tmdb_id: data.id },
            {
                $set: movie_document,
                $setOnInsert: { created_at: new Date() }
            },
            { upsert: true }
        );

        return data;
    } catch (error) {
        console.error(error);
        throw new Error("Failed to fetch movie");
    }
}

module.exports = { get_movie_by_id };