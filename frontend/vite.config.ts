import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// The desk API (backend/main.py) allows this exact origin: http://localhost:5173
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, strictPort: true },
})
