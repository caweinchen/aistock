import { describe, expect, it } from 'vitest';
import { getInitialAuthState } from './authSession';

describe('auth session state', () => {
  it('starts unauthenticated until the user submits login credentials', () => {
    expect(getInitialAuthState()).toBe(false);
  });
});
