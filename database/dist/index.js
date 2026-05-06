import express from "express";
import path from "path";
import { fileURLToPath } from "url";
import helmet from "helmet";
import cors from "cors";
import rate_limit from "express-rate-limit";
import { connect_mongo } from "./db.js";
import auth_router from "./routes/auth.js";
import movies_router from "./routes/movies.js";
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const app = express();
const PORT = 3000;
// Security middleware
app.use(helmet());
app.use(cors({ origin: ["http://localhost:5173", "http://localhost:3000"] }));
app.use(express.json());
// Rate limiting
const limiter = rate_limit({
    windowMs: 15 * 60 * 1000,
    max: 100,
    standardHeaders: true,
    legacyHeaders: false,
    message: { error: "Too many requests, please try again later" }
});
app.use("/api", limiter);
// Serve frontend static files
app.use(express.static(path.join(__dirname, "..", "..", "dist")));
// API routes
app.use("/api/auth", auth_router);
app.use("/api/movies", movies_router);
app.get("/api/test", (_req, res) => {
    res.json({ status: "ok" });
});
// Start server
connect_mongo().then(() => {
    app.listen(PORT, () => {
        console.log(`Server is running on http://localhost:${PORT}`);
    });
});
//# sourceMappingURL=index.js.map