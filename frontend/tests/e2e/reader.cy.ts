// tests/e2e/reader.cy.ts

const randomId = () => `${Date.now().toString().slice(-6)}_${Math.floor(Math.random() * 1000)}`;

describe('Full-Stack Reader E2E Journey', () => {
  
  // define variables here so they are accessible to all tests
  let readerUser: any;
  let creatorUser: any;
  
  const storyToCommentOn = {
    title: `E2E Story for Commenting ${randomId()}`,
    content: 'This is the story we will comment on.',
    tags: ['e2e', 'comments'],
  };
  
  const testComment = `This is a brand new E2E test comment! ${randomId()}`;

  // Before all tests, create FRESH users
// Before all tests, create the two users we need
  before(() => {
    // 1. Create the reader
    cy.request({
      method: 'POST',
      url: 'http://localhost:8000/auth/signup', 
      body: { ...readerUser },
      failOnStatusCode: false, // <-- Don't fail immediately
    }).then((res) => {
      // Expect 201 (Created) OR 409 (Already exists)
      expect(res.status).to.be.oneOf([201, 409]);
    });
    
    // 2. Create the creator
    cy.request({
      method: 'POST',
      url: 'http://localhost:8000/auth/signup', 
      body: { ...creatorUser }, 
      failOnStatusCode: false, // <-- Don't fail immediately
    }).then((res) => {
      // Expect 201 (Created) OR 409 (Already exists)
      expect(res.status).to.be.oneOf([201, 409]);
    });
  });

  // Before each test, log in as reader AND ensure story exists
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
    
    // 2. ARRANGE: Create the story to be commented on
    // We temporarily log in as the CREATOR via API to create one
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
        // Important: Don't fail if story already exists (idempotency for retries)
        failOnStatusCode: false 
      }).then((res) => {
        // It's okay if it's 201 (Created) or 409 (Already exists from prev run)
        expect(res.status).to.be.oneOf([201, 409]); 
      });
    });
  }); 

  it('can navigate to stories, add a comment, and see it appear', () => {
    // --- ACT ---
    cy.visit('/');
    
    // Wait for hydration
    cy.get('a[href="/profile"]', { timeout: 10000 }).should('be.visible');
    
    // Click Stories
    cy.get('a[href="/userStory"]').contains('Stories').click();
    
    // Wait for list and click card
    cy.url().should('include', '/userStory');
    cy.contains(storyToCommentOn.title, { timeout: 10000 }).should('be.visible').click();
    
    // Wait for detail page
    cy.url().should('include', '/userStory/');
    cy.contains('h1', storyToCommentOn.title).should('be.visible');
    cy.contains('Loading post...', { timeout: 10000 }).should('not.exist');
    
    // Comment
    cy.get('textarea[placeholder*="Share your thoughts"]').type(testComment);
    cy.get('button').contains('Post Comment').click();

    // --- ASSERT ---
    cy.contains(testComment, { timeout: 10000 }).should('be.visible');
    cy.get('textarea[placeholder*="Share your thoughts"]').should('have.value', '');
  });

});