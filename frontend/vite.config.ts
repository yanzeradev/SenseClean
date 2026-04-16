import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path' // Adicionamos o import do path

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  resolve: {
    alias: {
      // Aqui dizemos: "Sempre que ver '@', aponte para a pasta 'src'"
      "@": path.resolve(__dirname, "./src"),
    },
  },
})