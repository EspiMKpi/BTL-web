import mongoose, { Schema } from "mongoose";
const genre_schema = new Schema({
    genre_id: { type: Number, required: true, unique: true },
    name: { type: String, required: true, trim: true }
}, {
    timestamps: { createdAt: "created_at", updatedAt: "updated_at" }
});
genre_schema.index({ name: 1 });
export const Genre = mongoose.model("Genre", genre_schema);
//# sourceMappingURL=Genre.js.map