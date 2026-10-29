import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import path from 'path';

export default defineConfig({
  plugins: [react(), tailwindcss()],
  // One .env for the whole web app, in the project folder (only VITE_* variables are exposed)
  envDir: path.resolve(__dirname, '..'),
  server: {
    // Lets a tunnel (cloudflared) serve the app: the API goes through this server when VITE_API_URL is empty
    allowedHosts: ['.trycloudflare.com'],
    proxy: { '/api': { target: process.env.BACKEND_URL || 'http://localhost:8001', changeOrigin: true } },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
});
