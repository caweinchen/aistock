import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { StockSummary } from '../types';

const aliceStock: StockSummary = {
  code: '600519',
  name: 'Alice Stock',
  price: 1,
  change_percent: 0,
  score: 80,
  signal: 'buy',
};

const bobStock: StockSummary = {
  code: '000001',
  name: 'Bob Stock',
  price: 2,
  change_percent: 0,
  score: 60,
  signal: 'neutral',
};

describe('localDb user cache namespace', () => {
  let currentUserId: string | null;
  let values: Map<string, string>;

  beforeEach(() => {
    vi.resetModules();
    currentUserId = null;
    values = new Map<string, string>();
    vi.doMock('./storage', () => ({
      STORAGE_KEYS: { CACHE_PREFIX: 'cache_' },
      getUserId: () => currentUserId,
      getStoredUser: () => currentUserId,
      storage: {
        getItem: vi.fn(async (key: string) => values.get(key) ?? null),
        setItem: vi.fn(async (key: string, value: string) => {
          values.set(key, value);
        }),
        removeItem: vi.fn(async (key: string) => {
          values.delete(key);
        }),
        multiRemove: vi.fn(async (keys: string[]) => {
          keys.forEach((key) => values.delete(key));
        }),
      },
    }));
  });

  it('keeps stock list cache isolated per user', async () => {
    const { saveStocks, getStocks } = await import('./localDb');

    currentUserId = 'alice';
    await saveStocks([aliceStock]);

    currentUserId = 'bob';
    await saveStocks([bobStock]);

    currentUserId = 'alice';
    await expect(getStocks()).resolves.toEqual([aliceStock]);

    currentUserId = 'bob';
    await expect(getStocks()).resolves.toEqual([bobStock]);
  });
});
