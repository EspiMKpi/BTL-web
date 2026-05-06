import { type Request, type Response, type NextFunction } from "express";
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
export declare function auth_middleware(req: Request, res: Response, next: NextFunction): void;
export declare function sign_token(payload: AuthPayload): string;
//# sourceMappingURL=auth.d.ts.map