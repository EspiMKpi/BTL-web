import mongoose, { type Document } from "mongoose";
export interface UserDoc extends Document {
    email: string;
    password: string;
    username: string;
    created_at: Date;
    updated_at: Date;
    compare_password(candidate: string): Promise<boolean>;
}
export declare const User: mongoose.Model<UserDoc, {}, {}, {}, mongoose.Document<unknown, {}, UserDoc, {}, mongoose.DefaultSchemaOptions> & UserDoc & Required<{
    _id: mongoose.Types.ObjectId;
}> & {
    __v: number;
} & {
    id: string;
}, any, UserDoc>;
//# sourceMappingURL=User.d.ts.map