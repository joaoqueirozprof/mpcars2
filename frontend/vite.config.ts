import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') }
  },
  server: { port: 5173, host: true },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) return

          if (id.includes('recharts')) return 'charts'
          if (id.includes('@tanstack/react-query')) return 'query'
          if (id.includes('lucide-react')) return 'icons'

          return 'vendor'
        },
      },
    },
  },
})
