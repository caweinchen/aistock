import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('react-native', () => ({
  Platform: { OS: 'web' },
}));

function createMemoryStorage() {
  const values = new Map<string, string>();
  return {
    getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => {
      values.set(key, value);
    },
    removeItem: (key: string) => {
      values.delete(key);
    },
    clear: () => {
      values.clear();
    },
  };
}

describe('auth storage logout cleanup', () => {
  beforeEach(() => {
    vi.resetModules();
    const localStorage = createMemoryStorage();
    vi.stubGlobal('window', { localStorage });
  });

  it('clears offline token when auth token is cleared', async () => {
    const { clearAuthToken, getOfflineToken, isLoggedIn, setAuthToken, setOfflineToken } = await import('./storage');

    setAuthToken('online-token');
    setOfflineToken('offline-token');

    expect(isLoggedIn()).toBe(true);
    expect(getOfflineToken()).toBe('offline-token');

    clearAuthToken();

    expect(isLoggedIn()).toBe(false);
    expect(getOfflineToken()).toBeNull();
  });
});
