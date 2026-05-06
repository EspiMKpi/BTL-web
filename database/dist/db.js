import mongoose from "mongoose";
import dotenv from "dotenv";
dotenv.config();
const mongo_uri = process.env.MONGODB_URI || "";
const db_name = process.env.DB_NAME || "movie_db";
async function connect_mongo() {
    try {
        await mongoose.connect(mongo_uri, { dbName: db_name });
        console.log("Connected to MongoDB Atlas via Mongoose");
    }
    catch (err) {
        console.error("MongoDB connection error:", err);
        process.exit(1);
    }
}
export { connect_mongo };
//# sourceMappingURL=db.js.map