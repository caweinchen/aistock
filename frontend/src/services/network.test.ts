import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('./storage', () => ({
  getApiBaseUrl: () => 'http://server.test',
}));

describe('backend network status', () => {
  beforeEach(() => {
    vi.resetModules();
    vi.unstubAllGlobals();
  });

  it('reports offline when the device is online but the backend health check fails', async () => {
    vi.stubGlobal('navigator', { onLine: true });
    vi.stubGlobal('fetch', vi.fn(async () => {
      throw new TypeError('fetch failed');
    }));

    const { checkNetwork, isOffline } = await import('./network');

    await expect(checkNetwork()).resolves.toBe('offline');
    expect(isOffline()).toBe(true);
  });

  it('reports online when the backend health check succeeds', async () => {
    vi.stubGlobal('navigator', { onLine: true });
    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: true })));

    const { checkNetwork, isOnline } = await import('./network');

    await expect(checkNetwork()).resolves.toBe('online');
    expect(isOnline()).toBe(true);
  });
});
