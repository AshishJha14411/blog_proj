import { defineConfig } from 'cypress'

export default defineConfig({
  e2e: {
    // This is the URL of your Next.js app (from package.json "dev" script)
    baseUrl: 'http://localhost:3000',
    
    // This tells Cypress where to find your test files
    specPattern: 'tests/e2e/**/*.cy.{js,jsx,ts,tsx}',
    
    // We'll add this for a better experience
    supportFile: false,
    video: false,
  },
})