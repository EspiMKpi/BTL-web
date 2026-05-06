const { MongoClient } = require("mongodb");
require("dotenv").config();

// MongoDB Atlas Connection
const mongo_uri = process.env.MONGODB_URI;
const db_name = process.env.DB_NAME || "movie_db";

const mongo_client = new MongoClient(mongo_uri);

let db;
let movies_collection;

async function connect_mongo() {
    try {
        await mongo_client.connect();
        db = mongo_client.db(db_name);
        movies_collection = db.collection("movies");

        // Ensure indexes
        await movies_collection.createIndex({ tmdb_id: 1 }, { unique: true });
        await movies_collection.createIndex({ "genres.genre_id": 1 });
        await movies_collection.createIndex({ title: "text" });

        console.log("Connected to MongoDB Atlas");
    } catch (err) {
        console.error("MongoDB connection error:", err);
        process.exit(1);
    }
}

module.exports = { connect_mongo, mongo_client, get_db: () => db, get_movies_collection: () => movies_collection };