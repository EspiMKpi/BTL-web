import { type Request, type Response, type NextFunction } from "express";
import jwt from "jsonwebtoken";

const jwt_secret: string = process.env.JWT_SECRET || "vozflix_jwt_secret_change_me";

export interface AuthPayload {
    user_id: string;
    email: string;
}

declare global {
    namespace Express {
        interface Request {
            user?: AuthPayload;
        }
    }
}

export function auth_middleware(req: Request, res: Response, next: NextFunction): void {
    const auth_header = req.headers.authorization;
    if (!auth_header || !auth_header.startsWith("Bearer ")) {
        res.status(401).json({ error: "No token provided" });
        return;
    }

    const token = auth_header.substring(7);
    try {
        const decoded = jwt.verify(token, jwt_secret) as AuthPayload;
        req.user = decoded;
        next();
    } catch {
        res.status(401).json({ error: "Invalid or expired token" });
    }
}

/**
 * Optional auth: sets req.user if a valid token is present,
 * but does NOT reject unauthenticated requests.
 * Use on public routes that behave differently for logged-in users.
 */
export function optional_auth(req: Request, _res: Response, next: NextFunction): void {
    const auth_header = req.headers.authorization;
    if (auth_header && auth_header.startsWith("Bearer ")) {
        const token = auth_header.substring(7);
        try {
            req.user = jwt.verify(token, jwt_secret) as AuthPayload;
        } catch {
            // invalid token — proceed without user context
        }
    }
    next();
}

export function sign_token(payload: AuthPayload): string {
    return jwt.sign(payload, jwt_secret, { expiresIn: "7d" });
}
