import axios from "axios";
import { Movie } from "./models/Movie.js";
async function get_movie_by_id(tmdb_id) {
    try {
        const existing_doc = await Movie.findOne({ tmdb_id: tmdb_id });
        if (existing_doc && existing_doc.raw_data) {
            console.log("Serving from MongoDB");
            return existing_doc.raw_data;
        }
        console.log("Fetching everything from TMDB...");
        const response = await axios.get(`https://api.themoviedb.org/3/movie/${tmdb_id}?api_key=${process.env.TMDB_API_KEY}&append_to_response=credits`);
        const data = response.data;
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
        await Movie.updateOne({ tmdb_id: data.id }, {
            $set: movie_document,
            $setOnInsert: { created_at: new Date() }
        }, { upsert: true });
        return data;
    }
    catch (error) {
        console.error(error);
        throw new Error("Failed to fetch movie");
    }
}
export { get_movie_by_id };
//# sourceMappingURL=movieService.js.map