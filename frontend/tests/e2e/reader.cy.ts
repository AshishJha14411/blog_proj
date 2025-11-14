// tests/e2e/reader.cy.ts

// --- (Test Data setup is the same) ---
const readerUser = {
  username: `e2e_reader_${Date.now()}`,
  email: `e2e_reader_${Date.now()}@example.com`,
  password: 'Password123!',
};
const creatorUser = {
  username: `e2e_creator_${Date.now()}`,
  email: `e2e_creator_${Date.now()}@example.com`,
  password: 'Password123!',
};
const storyToCommentOn = {
  title: 'E2E Story for Commenting',
  content: 'This is the story we will comment on.',
  tags: ['e2e', 'comments'],
};
const testComment = 'This is a brand new E2E test comment!';

// --- E2E Test Suite ---
describe('Full-Stack Reader E2E Journey', () => {

  // --- (before() hook is the same) ---
  before(() => {
    // 1. Create the reader
    cy.request({
      method: 'POST',
      url: 'http://localhost:8000/auth/signup', 
      body: { ...readerUser },
    }).its('status').should('eq', 201);
    
    // 2. Create the creator
    cy.request({
      method: 'POST',
      url: 'http://localhost:8000/auth/signup', 
      body: { ...creatorUser }, // Backend rule will auto-promote
    }).its('status').should('eq', 201);
  });

  // --- (beforeEach() hook is the same) ---
  beforeEach(() => {
    // 1. Log in as the READER via API
    cy.request({
      method: 'POST',
      url: 'http://localhost:8000/auth/login',
      body: {
        username: readerUser.username,
        password: readerUser.password,
      },
    }).then((response) => {
      // 2. Set auth state in localStorage for Zustand
      const { access_token, refresh_token, user } = response.body;
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
    
    // 3. ARRANGE: Create the story to be commented on
    // We log in as the CREATOR and create one
    cy.request({
      method: 'POST',
      url: 'http://localhost:8000/auth/login',
      body: {
        username: creatorUser.username,
        password: creatorUser.password,
      },
    }).then((response) => {
      const token = response.body.access_token;
      cy.request({
        method: 'POST',
        url: 'http://localhost:8000/stories/',
        headers: { Authorization: `Bearer ${token}` },
        body: {
          title: storyToCommentOn.title,
          content: storyToCommentOn.content,
          tag_names: storyToCommentOn.tags,
          is_published: true,
        },
      }).its('status').should('eq', 201);
    });

  }); // End beforeEach

  it('can navigate to stories, add a comment, and see it appear', () => {
    
    // --- ACT ---
    // 1. Visit the homepage (as the logged-in READER)
    cy.visit('/');
    
    // 2. Wait for hydration (by finding the 'Profile' link)
    cy.get('a[href="/profile"]', { timeout: 10000 }).should('be.visible');
    
    // --- THIS IS THE FIX ---
    // 3. Click the "Stories" link in the Navbar
    cy.get('a[href="/userStory"]').contains('Stories').click();
    // --- END FIX ---
    
    // 4. Wait for the stories page to load and find the card
    cy.url().should('include', '/userStory');
    cy.contains(storyToCommentOn.title, { timeout: 10000 }).should('be.visible').click();
    
    // 5. Wait for the story detail page to load
    cy.url().should('include', '/userStory/');
    cy.contains('h1', storyToCommentOn.title).should('be.visible');
    cy.contains('Loading post...', { timeout: 10000 }).should('not.exist');
    
    // 6. Find the comment form, type, and submit
    cy.get('textarea[placeholder*="Share your thoughts"]').type(testComment);
    cy.get('button').contains('Post Comment').click();

    // --- ASSERT ---
    // 7. The new comment should appear
    cy.contains(testComment, { timeout: 10000 }).should('be.visible');

    // 8. The form should be cleared
    cy.get('textarea[placeholder*="Share your thoughts"]').should('have.value', '');
  });

});