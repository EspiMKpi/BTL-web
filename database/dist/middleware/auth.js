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
/**
 * Optional auth: sets req.user if a valid token is present,
 * but does NOT reject unauthenticated requests.
 * Use on public routes that behave differently for logged-in users.
 */
export function optional_auth(req, _res, next) {
    const auth_header = req.headers.authorization;
    if (auth_header && auth_header.startsWith("Bearer ")) {
        const token = auth_header.substring(7);
        try {
            req.user = jwt.verify(token, jwt_secret);
        }
        catch {
            // invalid token — proceed without user context
        }
    }
    next();
}
export function sign_token(payload) {
    return jwt.sign(payload, jwt_secret, { expiresIn: "7d" });
}
//# sourceMappingURL=auth.js.map