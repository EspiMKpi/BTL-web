import { defineConfig } from "vite";
import tailwindcss from "@tailwindcss/vite";
import path from "path";

export default defineConfig({
    root: "src",
    publicDir: path.resolve(__dirname, "public"),
    plugins: [tailwindcss()],
    build: {
        outDir: path.resolve(__dirname, "dist"),
        emptyOutDir: true
    },
    server: {
        port: 5173,
        proxy: {
            "/api": {
                target: "http://localhost:3000",
                changeOrigin: true
            }
        }
    }
});
