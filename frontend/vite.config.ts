import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import path from 'path';

export default defineConfig({
  plugins: [react(), tailwindcss()],
  // One .env for the whole web app, in the project folder (only VITE_* variables are exposed)
  envDir: path.resolve(__dirname, '..'),
  server: {
    // share-*.bat: a cloudflared tunnel serves the app, and the API goes through this server (VITE_API_URL=/)
    allowedHosts: ['.trycloudflare.com'],
    proxy: { '/api': { target: process.env.BACKEND_URL || 'http://localhost:8000', changeOrigin: true } },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
});
