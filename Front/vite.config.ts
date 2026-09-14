import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';
import path from 'path';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      injectRegister: 'auto',
      manifest: false,
      includeAssets: ['icon-192.svg', 'icon-512.svg'],
      workbox: {
        globPatterns: ['**/*.{js,css,html,ico,png,svg,woff2}'],
        runtimeCaching: [
          {
            urlPattern: /^https?:\/\/[abc]\.tile\.openstreetmap\.org\/.*$/i,
            handler: 'CacheFirst',
            options: {
              cacheName: 'osm-tiles-cache',
              expiration: {
                maxEntries: 200,
                maxAgeSeconds: 604800,
              },
              cacheableResponse: { statuses: [200] },
            },
          },
          {
            urlPattern: /^https?:\/\/[^/]+\/api\/events\/[^/]+\/zones(?:\/.*)?(?:\?.*)?$/i,
            handler: 'NetworkFirst',
            options: {
              cacheName: 'api-structural-cache',
              networkTimeoutSeconds: 3,
              expiration: {
                maxEntries: 50,
                maxAgeSeconds: 86400,
              },
              cacheableResponse: { statuses: [200] },
            },
          },
          {
            urlPattern: /^https?:\/\/[^/]+\/api\/(?:events\/[^/]+\/(?:products\/(?:parking|transport|gastronomy|bathroom|hydration|rest|accommodation|exit|health)|predictions|transport\/destinations)|emergencies|cities|emergency-protocols)/i,
            handler: 'NetworkFirst',
            options: {
              cacheName: 'api-dynamic-cache',
              networkTimeoutSeconds: 3,
              expiration: {
                maxEntries: 100,
                maxAgeSeconds: 900,
              },
              cacheableResponse: { statuses: [200] },
            },
          },
        ],
      },
    }),
  ],
  base: '/',  // CRÍTICO para Vercel (NO usar '/festivales-mocha')
  build: {
    outDir: 'dist',  // debe coincidir con vercel.json
    emptyOutDir: true,
    sourcemap: false
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  optimizeDeps: {
    exclude: ['lucide-react'],
  },
});
