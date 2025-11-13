// vitest.config.ts
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  root: __dirname,             // <- important
  plugins: [react()],

  resolve: {
    alias: {
      '@': path.resolve(__dirname, '.'),
      '@/components': path.resolve(__dirname, 'components'),
      '@/hooks': path.resolve(__dirname, 'hooks'),
      '@/lib': path.resolve(__dirname, 'lib'),
      '@/stores': path.resolve(__dirname, 'stores'),
    },
  },

  css: {
    modules: {
      generateScopedName: '[local]',
      localsConvention: 'camelCaseOnly',
    },
  },

  test: {
    root: __dirname,           // <- important for Vitest v4
    globals: true,
    environment: 'jsdom',
    setupFiles: './tests/setup.ts',

    // keep it simple & broad
    include: [
      '**/tests/**/*.test.ts',
      '**/tests/**/*.test.tsx',
      '**/tests/**/*.spec.ts',
      '**/tests/**/*.spec.tsx',
    ],
    exclude: [
      '**/node_modules/**',
      '**/.git/**',
      '**/dist/**',
      '**/build/**',
      '**/coverage/**',
    ],
  },
})
