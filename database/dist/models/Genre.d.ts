import mongoose, { type Document } from "mongoose";
export interface GenreDoc extends Document {
    genre_id: number;
    name: string;
    created_at: Date;
    updated_at: Date;
}
export declare const Genre: mongoose.Model<GenreDoc, {}, {}, {}, mongoose.Document<unknown, {}, GenreDoc, {}, mongoose.DefaultSchemaOptions> & GenreDoc & Required<{
    _id: mongoose.Types.ObjectId;
}> & {
    __v: number;
} & {
    id: string;
}, any, GenreDoc>;
//# sourceMappingURL=Genre.d.ts.map