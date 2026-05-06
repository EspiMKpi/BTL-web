import mongoose, { type Document } from "mongoose";
import type { WatchHistoryDocument } from "../types.js";
export interface WatchHistoryDoc extends Document, WatchHistoryDocument {
}
export declare const WatchHistory: mongoose.Model<WatchHistoryDoc, {}, {}, {}, mongoose.Document<unknown, {}, WatchHistoryDoc, {}, mongoose.DefaultSchemaOptions> & WatchHistoryDoc & Required<{
    _id: mongoose.Types.ObjectId;
}> & {
    __v: number;
} & {
    id: string;
}, any, WatchHistoryDoc>;
//# sourceMappingURL=WatchHistory.d.ts.map