import jwt from "jsonwebtoken";
const jwt_secret = process.env.JWT_SECRET || "vozflix_jwt_secret_change_me";
export function auth_middleware(req, res, next) {
    const auth_header = req.headers.authorization;
    if (!auth_header || !auth_header.startsWith("Bearer ")) {
        res.status(401).json({ error: "No token provided" });
        return;
    }
    const token = auth_header.substring(7);
    try {
        const decoded = jwt.verify(token, jwt_secret);
        req.user = decoded;
        next();
    }
    catch {
        res.status(401).json({ error: "Invalid or expired token" });
    }
}
export function sign_token(payload) {
    return jwt.sign(payload, jwt_secret, { expiresIn: "7d" });
}
//# sourceMappingURL=auth.js.map