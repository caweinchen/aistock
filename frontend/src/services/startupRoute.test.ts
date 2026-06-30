import { describe, expect, it } from 'vitest';
import { getStartupRouteState } from './startupRoute';

describe('startup route state', () => {
  it('starts on login without trusting cached auth state', () => {
    expect(getStartupRouteState()).toEqual({
      isLoggedIn: false,
      currentScreen: 'login',
    });
  });
});
