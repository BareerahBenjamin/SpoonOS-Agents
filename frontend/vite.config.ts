import { defineConfig } from 'vite'

const proxy = Object.fromEntries(
  ['health', 'settings', 'research', 'questions'].map((route) => [
    `^/${route}(?:[/?]|$)`,
    { target: 'http://127.0.0.1:8000' },
  ]),
)

export default defineConfig({
  esbuild: { jsx: 'automatic' },
  server: { proxy, strictPort: true },
  preview: { proxy },
})
