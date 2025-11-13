// tests/e2e/story.cy.ts

// This is our "creator" user for all tests in this file
const creatorUser = {
  // We include "creator" in the name so our backend service can auto-promote them
  username: `e2e_creator_${Date.now()}`,
  email: `e2e_creator_${Date.now()}@example.com`,
  password: 'Password123!',
};

// This is the data for the story we'll create
const testStory = {
  title: 'My E2E Test Story Title',
  content: 'This is the body of the story, written by Cypress.',
  tags: ['e2e', 'test', 'automation'],
};

describe('Full-Stack Story E2E Journey', () => {

  // Before all tests, create the "creator" user in the real database.
  before(() => {
    cy.request({
      method: 'POST',
      url: 'http://localhost:8000/auth/signup', 
      body: {
        username: creatorUser.username, // This username will trigger our backend fix
        email: creatorUser.email,
        password: creatorUser.password,
      },
    }).its('status').should('eq', 201);
  });

  // Before each individual test, log in programmatically
  beforeEach(() => {
    // 1. Log in via the API to get tokens
    cy.request({
      method: 'POST',
      url: 'http://localhost:8000/auth/login',
      body: {
        username: creatorUser.username,
        password: creatorUser.password,
      },
    }).then((response) => {
      // 2. Get the auth data from the response body
      const { access_token, refresh_token, user } = response.body;

      // 3. Set the refresh token in the cookie
      cy.setCookie('refresh_token', refresh_token, {
        httpOnly: true,
        secure: false, // Set to false for localhost
        path: '/auth',
      });

      // 4. Set the auth state in localStorage for Zustand
      const authState = {
        state: {
          accessToken: access_token,
          user: user,
          isAuthenticated: true,
          recentlyLoggedOut: false,
        },
        version: 0,
      };
      cy.window().its('localStorage').invoke('setItem', 'auth-storage', JSON.stringify(authState));
    });

    // 5. Visit the create page *after* auth is set
    cy.visit('/userStory/create');
  });

  it('allows a logged-in creator to create, publish, and view a new story', () => {
    
    // ASSERT 1: We are on the correct page
    cy.url().should('include', '/userStory/create');
    cy.contains('h1', 'Create a New Post').should('be.visible');

    // ACT: Fill out the form
    cy.get('input[id="title"]').type(testStory.title);
    cy.get('textarea[id="content"]').type(testStory.content);
    
    cy.get('input[placeholder*="Add tags"]').type(testStory.tags[0] + '{enter}');
    cy.get('input[placeholder*="Add tags"]').type(testStory.tags[1] + '{enter}');
    cy.get('input[placeholder*="Add tags"]').type(testStory.tags[2] + '{enter}');

    cy.contains(testStory.tags[0]).should('be.visible');

    // ACT: Submit the form
    cy.get('button[type="submit"]').contains('Publish Post').click();

    // ASSERT 2: We are redirected to the new story's page
    cy.url({ timeout: 10000 }).should('include', '/userStory/'); 

    // ASSERT 3: Wait for the loading message to disappear
    cy.contains('Loading post...', { timeout: 10000 }).should('not.exist');

    // ASSERT 4: The content we created is on the page
    cy.contains('h1', testStory.title).should('be.visible');
    
    // Use 'should('contain.text', ...)' for content set by dangerouslySetInnerHTML
    cy.get('article').should('contain.text', testStory.content);
    
    cy.contains(testStory.tags[0]).should('be.visible');
  });
});