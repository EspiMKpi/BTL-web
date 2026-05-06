import mongoose, { type Document } from "mongoose";
import type { WatchlistItemDocument } from "../types.js";
export interface WatchlistItemDoc extends Document, WatchlistItemDocument {
}
export declare const WatchlistItem: mongoose.Model<WatchlistItemDoc, {}, {}, {}, mongoose.Document<unknown, {}, WatchlistItemDoc, {}, mongoose.DefaultSchemaOptions> & WatchlistItemDoc & Required<{
    _id: mongoose.Types.ObjectId;
}> & {
    __v: number;
} & {
    id: string;
}, any, WatchlistItemDoc>;
//# sourceMappingURL=WatchlistItem.d.ts.map