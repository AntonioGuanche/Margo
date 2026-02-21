import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/auth/login': 'http://localhost:8000',
      '/auth/verify': 'http://localhost:8000',
      '/api': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    },
  },
})
