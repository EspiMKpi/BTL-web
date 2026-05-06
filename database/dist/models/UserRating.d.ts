import mongoose, { type Document } from "mongoose";
import type { UserRatingDocument } from "../types.js";
export interface UserRatingDoc extends Document, UserRatingDocument {
}
export declare const UserRating: mongoose.Model<UserRatingDoc, {}, {}, {}, mongoose.Document<unknown, {}, UserRatingDoc, {}, mongoose.DefaultSchemaOptions> & UserRatingDoc & Required<{
    _id: mongoose.Types.ObjectId;
}> & {
    __v: number;
} & {
    id: string;
}, any, UserRatingDoc>;
//# sourceMappingURL=UserRating.d.ts.map