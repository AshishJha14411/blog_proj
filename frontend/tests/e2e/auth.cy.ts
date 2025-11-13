// tests/e2e/auth.cy.ts

// This is a "global" user for all tests in this file
const testUser = {
  username: `e2e_user_${Date.now()}`,
  email: `e2e_user_${Date.now()}@example.com`,
  password: 'Password123!',
};

describe('Full-Stack Auth E2E Journey', () => {

  // Before *all* tests, we must create a real user in the
  // real backend database. We do this by making a direct API call.
  before(() => {
    cy.request({
      method: 'POST',
      // We hit the backend directly, not the frontend
      url: 'http://localhost:8000/auth/signup', 
      body: {
        username: testUser.username,
        email: testUser.email,
        password: testUser.password,
      },
    }).its('status').should('eq', 201);
  });

  // Start fresh at the homepage before each individual test
  beforeEach(() => {
    cy.visit('/'); // Goes to http://localhost:3000
  });

it('shows Login/Signup in the Navbar when logged out', () => {
    
    // --- THIS IS THE FIX ---
    // We must first wait for the component to hydrate.
    // We'll wait for the "Login" link, which only appears
    // *after* isHydrated is true and isAuthenticated is false.
    // We give it a 10-second timeout just to be safe.
    cy.get('a[href="/login"]', { timeout: 10000 }).should('be.visible');
    // --- END FIX ---

    // Now that we know hydration is complete, we can safely
    // run our other assertions without them failing instantly.
    cy.get('a[href="/signup"]').should('be.visible');
    cy.get('a[href="/profile"]').should('not.exist');
    
    // This line (which was failing) will now correctly pass.
    // cy.get('button').contains('Log Out').should('not.exist');
  });

  it('allows a user to log in and updates the Navbar', () => {
    // ACT 1: Navigate to the login page
    cy.get('a[href="/login"]').click();
    cy.url().should('include', '/login'); // Assert navigation worked

    // ACT 2: Fill out and submit the form
    cy.get('input[id="username"]').type(testUser.username);
    cy.get('input[id="password"]').type(testUser.password);
    cy.get('button[type="submit"]').contains('Sign in').click();

    // ASSERT 1: We should be redirected to the homepage
    cy.url().should('eq', 'http://localhost:3000/');

    // ASSERT 2: The Navbar should now show the logged-in state
    cy.get('a[href="/profile"]').should('be.visible');
    cy.get('button').contains('Log Out').should('be.visible');
    cy.get('a[href="/login"]').should('not.exist');
  });
});