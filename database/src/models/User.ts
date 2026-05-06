import mongoose, { Schema, type Document } from "mongoose";
import bcrypt from "bcryptjs";

export interface UserDoc extends Document {
    email: string;
    password: string;
    username: string;
    created_at: Date;
    updated_at: Date;
    compare_password(candidate: string): Promise<boolean>;
}

const user_schema = new Schema<UserDoc>({
    email: {
        type: String,
        required: true,
        unique: true,
        lowercase: true,
        trim: true
    },
    password: {
        type: String,
        required: true,
        select: false
    },
    username: {
        type: String,
        trim: true
    }
}, {
    timestamps: { createdAt: "created_at", updatedAt: "updated_at" }
});

user_schema.pre("save", async function () {
    if (!this.isModified("password")) return;
    this.password = await bcrypt.hash(this.password, 10);
    if (!this.username) {
        this.username = this.email.split("@")[0];
    }
});

user_schema.methods.compare_password = async function (candidate: string): Promise<boolean> {
    return bcrypt.compare(candidate, this.password);
};

export const User = mongoose.model<UserDoc>("User", user_schema);
