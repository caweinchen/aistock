import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

describe('useStockData offline-first initial load', () => {
  it('fetches and caches stocks on initial online load when local cache is empty', () => {
    const source = readFileSync(resolve(__dirname, 'useStockData.ts'), 'utf8');
    const loadStocksFromCacheBody = source.match(/const loadStocksFromCache = useCallback\(async \(\) => \{([\s\S]*?)\n  const refreshWatchlist = useCallback/);

    expect(loadStocksFromCacheBody?.[1]).toBeTruthy();
    expect(loadStocksFromCacheBody?.[1]).toContain("if (backendOffline)");
    expect(loadStocksFromCacheBody?.[1]).toContain('const onlineResult = await getStocks(true)');
    expect(loadStocksFromCacheBody?.[1]).toContain('getStocks(false)');
  });

  it('does not clear an existing offline status when cached detail has no offline flag', () => {
    const source = readFileSync(resolve(__dirname, 'useStockData.ts'), 'utf8');

    expect(source).toContain('setIsOffline((current) => result.isOffline ?? current)');
    expect(source).not.toContain('setIsOffline(result.isOffline ?? false)');
  });
});
