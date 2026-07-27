import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// A porta do backend vem de VITE_API_PORT para nao divergir do PORT do .env do
// Python. O default 8787 e o mesmo documentado no README — se voce mudar um,
// mude os dois.
const apiPort = process.env.VITE_API_PORT ?? '8787'
const port = Number(process.env.VITE_PORT ?? '5173')

export default defineConfig({
  plugins: [react()],
  server: {
    port,
    strictPort: true,
    proxy: {
      '/api': {
        target: `http://localhost:${apiPort}`,
        changeOrigin: true,
      },
      '/health': {
        target: `http://localhost:${apiPort}`,
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
  },
})
