// tests/e2e/negative.cy.ts
//
// Negative-path E2E flows. The other specs (auth/story/reader) all walk
// the happy path — these cases prove the UI degrades correctly when
// something is wrong. If any of them silently starts passing on a broken
// build, treat it as a regression, not a "yay it works".

const randomId = () => `${Date.now().toString().slice(-6)}_${Math.floor(Math.random() * 1000)}`;

describe('Negative flows', () => {
  it('shows an error when login credentials are wrong', () => {
    cy.visit('/login');
    cy.get('input[id="username"]').type(`ghost_${randomId()}`);
    cy.get('input[id="password"]').type('definitely-not-my-password');
    cy.get('button[type="submit"]').contains('Sign in').click();

    // We should still be on /login — the app must NOT redirect on failed auth.
    cy.url({ timeout: 10000 }).should('include', '/login');
    // No profile link should appear (would signal a false login).
    cy.get('a[href="/profile"]').should('not.exist');
    // Some kind of error surface should be present. Match loosely — the
    // exact copy can change without breaking the intent of this test.
    cy.contains(/invalid|incorrect|failed|wrong/i, { timeout: 10000 }).should('be.visible');
  });

  it('redirects an unauthenticated visitor away from /bookmarks', () => {
    // Make sure any leftover session is gone. cy.clearCookies handles the
    // refresh cookie; clearLocalStorage kills any zustand-persisted user.
    cy.clearCookies();
    cy.clearLocalStorage();

    cy.visit('/bookmarks');
    // Redirect target is /login (see BookmarksPage useEffect).
    cy.url({ timeout: 10000 }).should('include', '/login');
  });

  it('returns 404 UX when a story does not exist', () => {
    // A random UUID that no story owns.
    const missing = '00000000-0000-0000-0000-000000000000';
    cy.request({
      url: `http://localhost:8000/stories/${missing}`,
      failOnStatusCode: false,
    }).its('status').should('eq', 404);

    // The frontend detail page should also render an error state instead of
    // hanging on "Loading...".
    cy.visit(`/userStory/${missing}`, { failOnStatusCode: false });
    cy.contains(/not found|failed to load|404/i, { timeout: 10000 }).should('be.visible');
  });

  it('rejects a soft-deleted story on the details endpoint', () => {
    // Seed a creator + published story, delete it via the API, then verify
    // both the API and the UI treat it as gone.
    const creator = {
      username: `e2e_creator_${randomId()}`,
      email: `e2e_creator_${randomId()}@example.com`,
      password: 'Password123!',
    };

    cy.request({
      method: 'POST',
      url: 'http://localhost:8000/auth/signup',
      body: creator,
      failOnStatusCode: false,
    }).its('status').should('be.oneOf', [201, 409]);

    cy.request('POST', 'http://localhost:8000/auth/login', {
      username: creator.username,
      password: creator.password,
    }).then((login) => {
      const token = login.body.access_token as string;

      cy.request({
        method: 'POST',
        url: 'http://localhost:8000/stories/',
        headers: { Authorization: `Bearer ${token}` },
        body: {
          title: `soft-delete story ${randomId()}`,
          content: 'body body body',
          tag_names: ['negative'],
          is_published: true,
        },
      }).then((created) => {
        const storyId = created.body.id;

        // Soft-delete via the DELETE endpoint.
        cy.request({
          method: 'DELETE',
          url: `http://localhost:8000/stories/${storyId}`,
          headers: { Authorization: `Bearer ${token}` },
        }).its('status').should('be.oneOf', [200, 204]);

        // After soft-delete the details endpoint must 404 even to the owner
        // (W5 regression lock — mirrors test_get_story_details_404_when_soft_deleted).
        cy.request({
          method: 'GET',
          url: `http://localhost:8000/stories/${storyId}`,
          headers: { Authorization: `Bearer ${token}` },
          failOnStatusCode: false,
        }).its('status').should('eq', 404);
      });
    });
  });
});
