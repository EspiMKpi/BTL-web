import { Router } from "express";
import { User } from "../models/User.js";
import { auth_middleware, sign_token } from "../middleware/auth.js";
const router = Router();
router.post("/register", async (req, res) => {
    try {
        const { email, password } = req.body;
        if (!email || !password) {
            res.status(400).json({ error: "Email and password are required" });
            return;
        }
        if (password.length < 8) {
            res.status(400).json({ error: "Password must be at least 8 characters" });
            return;
        }
        const existing = await User.findOne({ email: email.toLowerCase() });
        if (existing) {
            res.status(409).json({ error: "Email already registered" });
            return;
        }
        const user = await User.create({ email, password });
        const token = sign_token({ user_id: user._id.toString(), email: user.email });
        res.status(201).json({
            token,
            user: { id: user._id, email: user.email, username: user.username }
        });
    }
    catch (error) {
        res.status(500).json({ error: error.message });
    }
});
router.post("/login", async (req, res) => {
    try {
        const { email, password } = req.body;
        if (!email || !password) {
            res.status(400).json({ error: "Email and password are required" });
            return;
        }
        const user = await User.findOne({ email: email.toLowerCase() }).select("+password");
        if (!user) {
            res.status(401).json({ error: "Invalid email or password" });
            return;
        }
        const is_match = await user.compare_password(password);
        if (!is_match) {
            res.status(401).json({ error: "Invalid email or password" });
            return;
        }
        const token = sign_token({ user_id: user._id.toString(), email: user.email });
        res.json({
            token,
            user: { id: user._id, email: user.email, username: user.username }
        });
    }
    catch (error) {
        res.status(500).json({ error: error.message });
    }
});
router.get("/me", auth_middleware, async (req, res) => {
    try {
        const user = await User.findById(req.user.user_id);
        if (!user) {
            res.status(404).json({ error: "User not found" });
            return;
        }
        res.json({ id: user._id, email: user.email, username: user.username });
    }
    catch (error) {
        res.status(500).json({ error: error.message });
    }
});
export default router;
//# sourceMappingURL=auth.js.map