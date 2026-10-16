import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Static site: relative base + HashRouter, so dist/ works on any static host (no server rewrites).
export default defineConfig({
  base: './',
  plugins: [react()],
  build: {
    outDir: 'dist',
    sourcemap: false,
    chunkSizeWarningLimit: 1500,
    rollupOptions: {
      output: {
        manualChunks: {
          three: ['three', '@react-three/fiber', '@react-three/drei'],
        },
      },
    },
  },
});
