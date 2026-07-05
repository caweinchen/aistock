import { beforeEach, describe, expect, it, vi } from 'vitest';

let hasAuthToken = false;
let offlineToken: string | null = null;

vi.mock('./storage', () => ({
  isLoggedIn: () => hasAuthToken,
  getOfflineToken: () => offlineToken,
}));

describe('auth session state', () => {
  beforeEach(() => {
    hasAuthToken = false;
    offlineToken = null;
  });

  it('starts unauthenticated when there is no local auth state', async () => {
    const { getInitialAuthState } = await import('./authSession');

    expect(getInitialAuthState()).toBe(false);
  });

  it('starts authenticated when an auth token exists locally', async () => {
    hasAuthToken = true;
    const { getInitialAuthState } = await import('./authSession');

    expect(getInitialAuthState()).toBe(true);
  });

  it('starts authenticated when an offline token exists locally', async () => {
    offlineToken = 'offline_alice_123';
    const { getInitialAuthState } = await import('./authSession');

    expect(getInitialAuthState()).toBe(true);
  });
});
