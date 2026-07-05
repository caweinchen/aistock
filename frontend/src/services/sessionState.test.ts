import { describe, expect, it } from 'vitest';
import { createSessionResetState, createUserSessionKey } from './sessionState';

describe('sessionState', () => {
  it('creates a user-scoped key so HomeScreen remounts after switching users', () => {
    const first = createUserSessionKey('alice', '1');
    const second = createUserSessionKey('bob', '2');

    expect(first).not.toBe(second);
    expect(first).toBe('alice:1');
    expect(second).toBe('bob:2');
  });

  it('clears selected stocks and search state for a new login session', () => {
    expect(createSessionResetState(4)).toEqual({
      isSearchVisible: false,
      pendingSearchQuery: null,
      refreshKey: 5,
      researchSnapshot: null,
      screenParams: {},
      searchQuery: '',
      selectedStockCode: undefined,
    });
  });
});
