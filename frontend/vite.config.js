import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In dev, forward API calls to the FastAPI server (uvicorn app:app --reload on port 8000).
export default defineConfig({
  plugins: [react()],
  server: { proxy: { "/api": "http://127.0.0.1:8000", "/health": "http://127.0.0.1:8000" } },
  build: { chunkSizeWarningLimit: 600 },
});
