import mongoose, { Schema, type Document } from "mongoose";
import bcrypt from "bcryptjs";

export interface UserDoc extends Document {
    email: string;
    password: string;
    username: string;
    avatar_url: string | null;
    role: "user" | "admin";
    is_active: boolean;
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
    },
    avatar_url: { type: String, default: null },
    role: { type: String, enum: ["user", "admin"], default: "user" },
    is_active: { type: Boolean, default: true }
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
