import { beforeEach, describe, expect, it, vi } from 'vitest';

let hasAuthToken = false;
let offlineToken: string | null = null;

vi.mock('./storage', () => ({
  isLoggedIn: () => hasAuthToken,
  getOfflineToken: () => offlineToken,
}));

describe('startup route state', () => {
  beforeEach(() => {
    hasAuthToken = false;
    offlineToken = null;
  });

  it('starts on login when no local auth state exists', async () => {
    const { getStartupRouteState } = await import('./startupRoute');

    expect(getStartupRouteState()).toEqual({
      isLoggedIn: false,
      currentScreen: 'login',
    });
  });

  it('starts on home when an auth token is cached', async () => {
    hasAuthToken = true;
    const { getStartupRouteState } = await import('./startupRoute');

    expect(getStartupRouteState()).toEqual({
      isLoggedIn: true,
      currentScreen: 'home',
    });
  });

  it('starts on home when an offline token is cached', async () => {
    offlineToken = 'offline_alice_123';
    const { getStartupRouteState } = await import('./startupRoute');

    expect(getStartupRouteState()).toEqual({
      isLoggedIn: true,
      currentScreen: 'home',
    });
  });
});
