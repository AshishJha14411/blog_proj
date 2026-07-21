import { defineConfig } from 'cypress'

export default defineConfig({
  e2e: {
    // This is the URL of your Next.js app (from package.json "dev" script)
    baseUrl: 'http://localhost:3000',

    // This tells Cypress where to find your test files
    specPattern: 'tests/e2e/**/*.cy.{js,jsx,ts,tsx}',

    supportFile: false,
    // Capture on CI so failed runs are diagnosable from the artifact tab.
    video: true,
    screenshotOnRunFailure: true,
  },
})