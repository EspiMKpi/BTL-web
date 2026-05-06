import mongoose, { Schema, type Document } from "mongoose";

export interface GenreDoc extends Document {
    genre_id: number;
    name: string;
    created_at: Date;
    updated_at: Date;
}

const genre_schema = new Schema<GenreDoc>({
    genre_id: { type: Number, required: true, unique: true },
    name: { type: String, required: true, trim: true }
}, {
    timestamps: { createdAt: "created_at", updatedAt: "updated_at" }
});

genre_schema.index({ name: 1 });

export const Genre = mongoose.model<GenreDoc>("Genre", genre_schema);
