# Offline-First Login and App Cache Implementation Plan

## Current Decision Status

- [ ] TODO: Owner `frontend machine` — 由用户重新确认是否将本计划作为下一前端切片；确认前状态为 `Needs Decision`，不得由历史复选框自动启动实现。
- [ ] TODO: Owner `frontend machine` — 如果获批，开始前重新核对 Expo 56 文档、当前依赖、现有缓存实现和 Gitee `main` 基准，并将本计划拆成当前可执行的聚焦前端计划。

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Expo app open to login first and render normal pages from app-local cache unless the user explicitly refreshes or performs a server action.

**Architecture:** Put persistence behind `localDb.ts`, keep server/cache policy in `api.ts`, and keep screens focused on loading cache on entry and refreshing only from refresh actions. Native Expo builds use AsyncStorage through the existing dependency, while web continues to use `window.localStorage`.

**Tech Stack:** Expo SDK `~56.0.12`, React Native `0.85.3`, React `19.2.3`, TypeScript `~6.0.3`, `@react-native-async-storage/async-storage` `2.2.0`, Node test runner or Vitest if needed.

## Global Constraints

- Read the exact versioned Expo docs at `https://docs.expo.dev/versions/v56.0.0/` before code changes.
- The app must open to the login page first.
- Normal page navigation must render from data cached inside the app.
- The app should contact the server only on explicit refresh or explicit server actions: login, search, watchlist updates, and backtest creation.
- Offline login, offline watchlist mutation, offline backtest creation, background sync, conflict resolution, and queued writes are out of scope.
- Cache misses are not fatal load failures.
- Network refresh failures preserve cached UI.
- Do not modify unrelated files or revert existing user changes.

---

## File Structure

- Modify `frontend/src/services/localDb.ts`
  Own typed cached data and platform storage. Add AsyncStorage support and helpers for stocks, search results, stock detail, strategy detail, dividends, news, institution holdings, and timestamps.

- Modify `frontend/src/services/api.ts`
  Separate cache-only reads from explicit server refreshes. Default reads do not call `fetch`. Refresh paths call `fetch`, save cache, and fall back to cache on failure.

- Modify `frontend/src/hooks/useStockData.ts`
  Load cached stocks on mount, use explicit refresh for server fetches, and keep existing cached data when refresh fails.

- Modify `frontend/src/pages/StockDetailScreen.tsx`
  Load cached detail and secondary sections on entry. Refresh fetches detail, dividends, news, and institution holdings.

- Modify `frontend/App.tsx`
  Add explicit startup/loading state, unauthenticated login route, and logout-to-login behavior.

- Create or modify frontend tests
  Add focused tests for storage/cache policy and navigation state. If no runner exists, add a minimal test runner dependency and script in `frontend/package.json`.

---

### Task 1: Add Frontend Test Harness

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`
- Create: `frontend/src/test/setup.ts`

**Interfaces:**
- Produces: `npm test -- --run` or equivalent frontend test command for later tasks.
- Produces: test setup that can mock `fetch`, `window.localStorage`, and AsyncStorage-like modules.

- [ ] **Step 1: Inspect current frontend dependencies**

Run: `npm pkg get scripts devDependencies` from `frontend`

Expected: no existing `test` script and no existing frontend test runner.

- [ ] **Step 2: Add a failing smoke test command**

Modify `frontend/package.json` to add:

```json
{
  "scripts": {
    "test": "vitest --environment node"
  },
  "devDependencies": {
    "vitest": "^3.2.0"
  }
}
```

Preserve existing scripts and devDependencies.

- [ ] **Step 3: Install dependencies**

Run: `npm install` from `frontend`

Expected: `package-lock.json` updates and `vitest` is installed.

- [ ] **Step 4: Create test setup**

Create `frontend/src/test/setup.ts`:

```ts
export function createMemoryStorage() {
  const map = new Map<string, string>();
  return {
    getItem: (key: string) => map.get(key) ?? null,
    setItem: (key: string, value: string) => {
      map.set(key, value);
    },
    removeItem: (key: string) => {
      map.delete(key);
    },
    clear: () => {
      map.clear();
    },
    key: (index: number) => Array.from(map.keys())[index] ?? null,
    get length() {
      return map.size;
    },
  };
}
```

- [ ] **Step 5: Run test command**

Run: `npm test -- --run` from `frontend`

Expected: exits successfully with "No test files found" or equivalent no-tests result. If Vitest exits non-zero for no tests, create `frontend/src/test/smoke.test.ts`:

```ts
import { describe, expect, it } from 'vitest';

describe('test harness', () => {
  it('runs frontend tests', () => {
    expect(true).toBe(true);
  });
});
```

Then rerun: `npm test -- --run`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/src/test/setup.ts frontend/src/test/smoke.test.ts
git commit -m "test: add frontend test harness"
```

If `smoke.test.ts` was not needed, omit it from `git add`.

---

### Task 2: Implement Native/Web Local Cache Storage

**Files:**
- Modify: `frontend/src/services/localDb.ts`
- Test: `frontend/src/services/localDb.test.ts`

**Interfaces:**
- Produces: `saveStocks(stocks: StockSummary[]): Promise<void>`
- Produces: `getStocks(): Promise<StockSummary[] | null>`
- Produces: `saveSearchResults(query: string, stocks: StockSummary[]): Promise<void>`
- Produces: `getSearchResults(query: string): Promise<StockSummary[] | null>`
- Produces: `saveStockDetail(code: string, detail: StockDetail): Promise<void>`
- Produces: `getStockDetail(code: string): Promise<StockDetail | null>`
- Produces: `saveStrategyDetail(code: string, strategyId: string, detail: StrategyDetail): Promise<void>`
- Produces: `getStrategyDetail(code: string, strategyId: string): Promise<StrategyDetail | null>`
- Produces: `saveDividendRecords(code: string, records: DividendRecord[]): Promise<void>`
- Produces: `getDividendRecords(code: string): Promise<DividendRecord[] | null>`
- Produces: `saveStockNews(code: string, news: StockNews[]): Promise<void>`
- Produces: `getStockNews(code: string): Promise<StockNews[] | null>`
- Produces: `saveInstitutionHoldings(code: string, records: InstHoldRecord[]): Promise<void>`
- Produces: `getInstitutionHoldings(code: string): Promise<InstHoldRecord[] | null>`
- Produces: `getLastUpdateTime(scope?: string): Promise<number | null>`

- [ ] **Step 1: Write failing localDb tests**

Create `frontend/src/services/localDb.test.ts`:

```ts
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { StockDetail, StockSummary, StrategyDetail, DividendRecord, StockNews, InstHoldRecord } from '../types';
import { createMemoryStorage } from '../test/setup';

vi.mock('@react-native-async-storage/async-storage', () => {
  const storage = createMemoryStorage();
  return {
    default: {
      getItem: vi.fn(async (key: string) => storage.getItem(key)),
      setItem: vi.fn(async (key: string, value: string) => storage.setItem(key, value)),
      removeItem: vi.fn(async (key: string) => storage.removeItem(key)),
      multiRemove: vi.fn(async (keys: string[]) => keys.forEach((key) => storage.removeItem(key))),
      getAllKeys: vi.fn(async () => Array.from({ length: storage.length }, (_, index) => storage.key(index)).filter(Boolean)),
    },
  };
});

const stock: StockSummary = {
  code: '000001.SZ',
  name: 'Ping An Bank',
  price: 10,
  change_percent: 1.2,
  score: 88,
  signal: 'buy',
};

const detail: StockDetail = {
  stock,
  factors: [{ key: 'value', label: 'Value', value: 80, description: 'cheap' }],
  strategies: [{ id: 'trend', name: 'Trend', period: '30d', return_rate: 5, max_drawdown: 2, win_rate: 60, risk: 'medium', summary: 'ok' }],
  alerts: [],
  history: [{ date: '2026-06-29', close: 10, volume: 1000 }],
  ai_summary: 'summary',
  data_status: 'cached',
  updated_at: '2026-06-29T00:00:00Z',
};

const strategyDetail: StrategyDetail = {
  strategy: detail.strategies[0],
  annualized_return: 12,
  sharpe_ratio: 1.1,
  trade_count: 2,
  rules: ['buy high'],
  trades: [{ date: '2026-06-01', action: 'buy', price: 9, quantity: 100, reason: 'signal' }],
};

const dividend: DividendRecord[] = [{
  ts_code: stock.code,
  div_proc: '实施',
  ann_date: '20260601',
  record_date: '20260610',
  ex_date: '20260611',
  pay_date: '20260612',
  div_cash: 0.1,
  bonus_share: 0,
  transfer_share: 0,
}];

const news: StockNews[] = [{
  ts_code: stock.code,
  title: 'News',
  content: 'Content',
  pub_time: '2026-06-29 09:00:00',
  source: 'Sina',
}];

const instHold: InstHoldRecord[] = [{
  ts_code: stock.code,
  trade_date: '20260629',
  inst_type: 'Fund',
  hold_amount: 100,
  hold_ratio: 1.5,
  change_amount: 10,
  change_ratio: 0.1,
}];

describe('localDb', () => {
  beforeEach(() => {
    vi.resetModules();
    vi.unstubAllGlobals();
  });

  it('stores and reads stock list and normalized search results', async () => {
    vi.stubGlobal('window', undefined);
    const localDb = await import('./localDb');

    await localDb.saveStocks([stock]);
    await localDb.saveSearchResults(' Ping ', [stock]);

    expect(await localDb.getStocks()).toEqual([stock]);
    expect(await localDb.getSearchResults('ping')).toEqual([stock]);
  });

  it('stores and reads all stock detail sections in native storage', async () => {
    vi.stubGlobal('window', undefined);
    const localDb = await import('./localDb');

    await localDb.saveStockDetail(stock.code, detail);
    await localDb.saveStrategyDetail(stock.code, 'trend', strategyDetail);
    await localDb.saveDividendRecords(stock.code, dividend);
    await localDb.saveStockNews(stock.code, news);
    await localDb.saveInstitutionHoldings(stock.code, instHold);

    expect(await localDb.getStockDetail(stock.code)).toEqual(detail);
    expect(await localDb.getStrategyDetail(stock.code, 'trend')).toEqual(strategyDetail);
    expect(await localDb.getDividendRecords(stock.code)).toEqual(dividend);
    expect(await localDb.getStockNews(stock.code)).toEqual(news);
    expect(await localDb.getInstitutionHoldings(stock.code)).toEqual(instHold);
  });

  it('returns null for malformed cache entries instead of throwing', async () => {
    const storage = createMemoryStorage();
    vi.stubGlobal('window', { localStorage: storage });
    const localDb = await import('./localDb');

    storage.setItem('local_stocks', '{broken');

    expect(await localDb.getStocks()).toBeNull();
  });
});
```

- [ ] **Step 2: Run tests to verify failure**

Run: `npm test -- --run src/services/localDb.test.ts` from `frontend`

Expected: FAIL because new helper functions do not exist and native AsyncStorage path is not implemented.

- [ ] **Step 3: Implement localDb storage helpers**

Modify `frontend/src/services/localDb.ts` to:

```ts
import type { DividendRecord, InstHoldRecord, StockDetail, StockNews, StockSummary, StrategyDetail } from '../types';

const DB_KEYS = {
  STOCKS: 'local_stocks',
  SEARCH_PREFIX: 'local_stock_search_',
  STOCK_DETAIL_PREFIX: 'local_stock_detail_',
  STRATEGY_DETAIL_PREFIX: 'local_strategy_detail_',
  DIVIDEND_PREFIX: 'local_stock_dividend_',
  NEWS_PREFIX: 'local_stock_news_',
  INST_HOLD_PREFIX: 'local_stock_inst_hold_',
  LAST_UPDATE_PREFIX: 'local_last_update_',
};

let AsyncStorage: any | null = null;
try {
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  const mod = require('@react-native-async-storage/async-storage');
  AsyncStorage = mod && (mod.default || mod);
} catch {
  AsyncStorage = null;
}

function getWebStorage(): Storage | null {
  try {
    if (typeof window !== 'undefined' && window.localStorage) return window.localStorage;
  } catch {
    return null;
  }
  return null;
}

function normalizeQuery(query: string): string {
  return query.trim().toLowerCase();
}

async function setString(key: string, value: string): Promise<void> {
  const webStorage = getWebStorage();
  if (webStorage) {
    webStorage.setItem(key, value);
    return;
  }
  if (AsyncStorage) {
    await AsyncStorage.setItem(key, value);
  }
}

async function getString(key: string): Promise<string | null> {
  const webStorage = getWebStorage();
  if (webStorage) return webStorage.getItem(key);
  if (AsyncStorage) return AsyncStorage.getItem(key);
  return null;
}

async function removeString(key: string): Promise<void> {
  const webStorage = getWebStorage();
  if (webStorage) {
    webStorage.removeItem(key);
    return;
  }
  if (AsyncStorage) {
    await AsyncStorage.removeItem(key);
  }
}

async function saveJson(key: string, data: unknown): Promise<void> {
  try {
    await setString(key, JSON.stringify(data));
    await setString(`${DB_KEYS.LAST_UPDATE_PREFIX}${key}`, Date.now().toString());
  } catch (e) {
    console.warn(`Failed to save local cache ${key}:`, e);
  }
}

async function getJson<T>(key: string): Promise<T | null> {
  try {
    const stored = await getString(key);
    if (!stored) return null;
    return JSON.parse(stored) as T;
  } catch (e) {
    console.warn(`Failed to read local cache ${key}:`, e);
    return null;
  }
}
```

Then implement exported functions using `saveJson/getJson` and keys from the interface list. Keep existing function names compatible.

- [ ] **Step 4: Implement clearLocalData for both platforms**

Update `clearLocalData` so web removes keys starting with all local prefixes, and native uses `AsyncStorage.getAllKeys()` plus `multiRemove()`. If `getAllKeys` is unavailable, remove only known non-prefix keys.

- [ ] **Step 5: Run tests to verify pass**

Run: `npm test -- --run src/services/localDb.test.ts` from `frontend`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/services/localDb.ts frontend/src/services/localDb.test.ts
git commit -m "feat: persist stock cache across app platforms"
```

---

### Task 3: Make API Reads Cache-Only by Default

**Files:**
- Modify: `frontend/src/services/api.ts`
- Test: `frontend/src/services/api.test.ts`

**Interfaces:**
- Consumes Task 2 localDb helpers.
- Produces: `getStocks(options?: { forceRefresh?: boolean }): Promise<StockSummary[]>`
- Produces: `searchStocks(keyword: string): Promise<StockSummary[]>`
- Produces: `getStockDetail(code: string, forceRefresh?: boolean): Promise<StockDetail>`
- Produces: `getStrategyDetail(code: string, strategyId: string, options?: { forceRefresh?: boolean }): Promise<StrategyDetail>`
- Produces: `getStockDividend(code: string, options?: { forceRefresh?: boolean }): Promise<DividendRecord[]>`
- Produces: `getStockNews(code: string, options?: { forceRefresh?: boolean }): Promise<StockNews[]>`
- Produces: `getStockInstHold(code: string, options?: { forceRefresh?: boolean }): Promise<InstHoldRecord[]>`
- Keeps: `refreshAllStocks(): Promise<StockSummary[]>` as explicit server refresh.

- [ ] **Step 1: Write failing API cache-policy tests**

Create `frontend/src/services/api.test.ts`:

```ts
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { StockDetail, StockSummary } from '../types';

const stock: StockSummary = {
  code: '000001.SZ',
  name: 'Ping An Bank',
  price: 10,
  change_percent: 1.2,
  score: 88,
  signal: 'buy',
};

const detail: StockDetail = {
  stock,
  factors: [],
  strategies: [],
  alerts: [],
  history: [],
  ai_summary: 'cached',
  data_status: 'cached',
  updated_at: '2026-06-29T00:00:00Z',
};

vi.mock('./storage', () => ({
  getApiBaseUrl: () => 'http://server.test',
  getAuthToken: () => 'token',
}));

describe('api cache policy', () => {
  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
    vi.unstubAllGlobals();
  });

  it('getStocks returns cached data without calling fetch', async () => {
    vi.doMock('./localDb', () => ({
      getStocks: vi.fn(async () => [stock]),
      saveStocks: vi.fn(),
      getSearchResults: vi.fn(),
      saveSearchResults: vi.fn(),
      getStockDetail: vi.fn(),
      saveStockDetail: vi.fn(),
    }));
    const fetchSpy = vi.fn();
    vi.stubGlobal('fetch', fetchSpy);
    const { getStocks } = await import('./api');

    await expect(getStocks()).resolves.toEqual([stock]);
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it('getStockDetail returns cached data without calling fetch', async () => {
    vi.doMock('./localDb', () => ({
      getStocks: vi.fn(),
      saveStocks: vi.fn(),
      getSearchResults: vi.fn(),
      saveSearchResults: vi.fn(),
      getStockDetail: vi.fn(async () => detail),
      saveStockDetail: vi.fn(),
    }));
    const fetchSpy = vi.fn();
    vi.stubGlobal('fetch', fetchSpy);
    const { getStockDetail } = await import('./api');

    await expect(getStockDetail(stock.code)).resolves.toEqual(detail);
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it('force refresh fetches server data and saves cache', async () => {
    const saveStockDetail = vi.fn();
    vi.doMock('./localDb', () => ({
      getStocks: vi.fn(),
      saveStocks: vi.fn(),
      getSearchResults: vi.fn(),
      saveSearchResults: vi.fn(),
      getStockDetail: vi.fn(async () => detail),
      saveStockDetail,
    }));
    const fresh = { ...detail, ai_summary: 'fresh', data_status: 'fresh' };
    vi.stubGlobal('fetch', vi.fn(async () => ({
      ok: true,
      json: async () => fresh,
    })));
    const { getStockDetail } = await import('./api');

    await expect(getStockDetail(stock.code, true)).resolves.toEqual(fresh);
    expect(saveStockDetail).toHaveBeenCalledWith(stock.code, fresh);
  });

  it('force refresh falls back to cache when server fails', async () => {
    vi.doMock('./localDb', () => ({
      getStocks: vi.fn(),
      saveStocks: vi.fn(),
      getSearchResults: vi.fn(),
      saveSearchResults: vi.fn(),
      getStockDetail: vi.fn(async () => detail),
      saveStockDetail: vi.fn(),
    }));
    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: false, json: async () => ({}) })));
    const { getStockDetail } = await import('./api');

    await expect(getStockDetail(stock.code, true)).resolves.toEqual(detail);
  });
});
```

- [ ] **Step 2: Run tests to verify failure**

Run: `npm test -- --run src/services/api.test.ts` from `frontend`

Expected: FAIL because `getStocks` and `getStockDetail` still call fetch by default.

- [ ] **Step 3: Refactor api fetch helpers**

In `frontend/src/services/api.ts`, add:

```ts
interface ReadOptions {
  forceRefresh?: boolean;
}

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${getApiBase()}${path}`, init);
  if (!response.ok) throw new Error('network');
  return response.json() as Promise<T>;
}

function cacheMiss(errorKey: string): never {
  throw new Error(errorKey);
}
```

Use `fetchJson` for all server reads.

- [ ] **Step 4: Implement cache-only default stock reads**

Change `getStocks`:

```ts
export async function getStocks(options: ReadOptions = {}): Promise<StockSummary[]> {
  if (!options.forceRefresh) {
    const localData = await getLocalStocks();
    if (localData) return localData;
    return [];
  }

  try {
    const data = await fetchJson<StockSummary[]>('/api/stocks', { headers: getAuthHeaders() });
    setCached('stocks', data);
    await saveStocks(data);
    return data;
  } catch (err) {
    const localData = await getLocalStocks();
    if (localData) return localData;
    throw new Error('fetchStocks');
  }
}
```

Change `refreshAllStocks` to call `getStocks({ forceRefresh: true })` or keep direct fetch with identical fallback and cache saving.

- [ ] **Step 5: Implement cache-aware stock detail reads**

Change `getStockDetail`:

```ts
export async function getStockDetail(code: string, forceRefresh = false): Promise<StockDetail> {
  if (!forceRefresh) {
    const cached = getCached<StockDetail>(`stock:${code}`);
    if (cached) return cached;
    const localData = await getLocalStockDetail(code);
    if (localData) {
      setCached(`stock:${code}`, localData);
      return localData;
    }
    return cacheMiss('fetchStockDetail');
  }

  cache.delete(`stock:${code}`);
  try {
    const data = await fetchJson<StockDetail>(`/api/stocks/${code}`, { headers: getAuthHeaders() });
    setCached(`stock:${code}`, data);
    await saveStockDetail(code, data);
    return data;
  } catch (err) {
    const localData = await getLocalStockDetail(code);
    if (localData) return localData;
    throw new Error('fetchStockDetail');
  }
}
```

- [ ] **Step 6: Implement cache-aware secondary reads**

Update imports from `localDb` and make these functions use cache by default and fetch only with `forceRefresh`:

```ts
export async function getStrategyDetail(code: string, strategyId: string, options: ReadOptions = {}): Promise<StrategyDetail> {
  const cacheKey = `strategy:${code}:${strategyId}`;
  if (!options.forceRefresh) {
    const cached = getCached<StrategyDetail>(cacheKey);
    if (cached) return cached;
    const localData = await getLocalStrategyDetail(code, strategyId);
    if (localData) {
      setCached(cacheKey, localData);
      return localData;
    }
  }

  try {
    const data = await fetchJson<StrategyDetail>(`/api/stocks/${code}/strategies/${strategyId}`, { headers: getAuthHeaders() });
    setCached(cacheKey, data);
    await saveStrategyDetail(code, strategyId, data);
    return data;
  } catch {
    const localData = await getLocalStrategyDetail(code, strategyId);
    if (localData) return localData;
    throw new Error('fetchStrategy');
  }
}

export async function getStockDividend(code: string, options: ReadOptions = {}): Promise<DividendRecord[]> {
  if (!options.forceRefresh) return (await getLocalDividendRecords(code)) ?? [];
  try {
    const data = await fetchJson<DividendRecord[]>(`/api/stocks/${code}/dividend`, { headers: getAuthHeaders() });
    await saveDividendRecords(code, data);
    return data;
  } catch {
    return (await getLocalDividendRecords(code)) ?? [];
  }
}

export async function getStockNews(code: string, options: ReadOptions = {}): Promise<StockNews[]> {
  if (!options.forceRefresh) return (await getLocalStockNews(code)) ?? [];
  try {
    const data = await fetchJson<StockNews[]>(`/api/stocks/${code}/news`, { headers: getAuthHeaders() });
    await saveStockNews(code, data);
    return data;
  } catch {
    return (await getLocalStockNews(code)) ?? [];
  }
}

export async function getStockInstHold(code: string, options: ReadOptions = {}): Promise<InstHoldRecord[]> {
  if (!options.forceRefresh) return (await getLocalInstitutionHoldings(code)) ?? [];
  try {
    const data = await fetchJson<InstHoldRecord[]>(`/api/stocks/${code}/inst-hold`, { headers: getAuthHeaders() });
    await saveInstitutionHoldings(code, data);
    return data;
  } catch {
    return (await getLocalInstitutionHoldings(code)) ?? [];
  }
}
```

For cache miss on list-like secondary sections, return `[]` rather than throwing.

- [ ] **Step 7: Keep search as explicit server action**

Change `searchStocks(keyword: string)` so it:

1. Returns `getStocks()` for blank query.
2. Fetches `/api/stocks/search?q=...`.
3. Saves successful results with `saveSearchResults(keyword, data)`.
4. On failure, returns `getSearchResults(keyword)`, then `getStocks()`, then `[]`.

- [ ] **Step 8: Run tests**

Run: `npm test -- --run src/services/api.test.ts` from `frontend`

Expected: PASS.

- [ ] **Step 9: Commit**

```bash
git add frontend/src/services/api.ts frontend/src/services/api.test.ts
git commit -m "feat: make stock reads cache first"
```

---

### Task 4: Update Home Data Flow

**Files:**
- Modify: `frontend/src/hooks/useStockData.ts`

**Interfaces:**
- Consumes Task 3 API behavior.
- Produces: mount load reads cache only.
- Produces: `refreshWatchlist()` performs server refresh only from refresh button.
- Produces: search submit remains explicit server action through `loadStocks(query)`.

- [ ] **Step 1: Write failing hook-level expectation**

If a hook test setup is practical, create `frontend/src/hooks/useStockData.test.tsx` using a React hook test utility. If not, cover this task through `api.test.ts` plus manual verification in Task 6. Do not add production code before either a hook test exists or the API tests from Task 3 protect the network policy.

- [ ] **Step 2: Make `loadStocks` preserve cached UI on failures**

In `useStockData.ts`, ensure the catch block does not clear `stocks` or `detail`. Keep:

```ts
const payload = await (query ? searchStocks(query) : getStocks());
setStocks(payload);
```

Because Task 3 makes `getStocks()` cache-only and `searchStocks()` explicit server action with fallback.

- [ ] **Step 3: Select first cached detail without server fetch**

When `payload.length > 0 && !selectedCodeRef.current`, keep `await loadStockDetail(payload[0].code)`. Task 3 makes `loadStockDetail` cache-only by default through `getStockDetail(code)`.

- [ ] **Step 4: Keep refresh as explicit server action**

Change `refreshWatchlist` to call `refreshAllStocks()` and then `loadStockDetail(selectedCodeRef.current, true)` only after adjusting `loadStockDetail` to accept `forceRefresh`.

Update signature:

```ts
const loadStockDetail = useCallback(async (code: string, forceRefresh = false) => {
  // ...
  const payload = await getStockDetail(code, forceRefresh);
  // ...
}, []);
```

- [ ] **Step 5: Run verification**

Run: `npm test -- --run src/services/api.test.ts src/services/localDb.test.ts` from `frontend`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/hooks/useStockData.ts
git commit -m "feat: load home data from cache by default"
```

---

### Task 5: Update Detail Page Offline Flow

**Files:**
- Modify: `frontend/src/pages/StockDetailScreen.tsx`

**Interfaces:**
- Consumes Task 3 API read options.
- Produces: entry load reads cached detail, dividends, news, institution holdings.
- Produces: refresh fetches detail and secondary sections with `{ forceRefresh: true }`.
- Produces: cached detail remains visible if refresh fails.

- [ ] **Step 1: Confirm entry load currently forces server**

Find in `StockDetailScreen.tsx`:

```ts
void loadDetail(true);
```

Expected: present before implementation.

- [ ] **Step 2: Change mount load to cache-only**

Replace mount effect body with:

```ts
void loadDetail(false);
void loadInstHold(false);
void loadDividend(false);
void loadNews(false);
```

Update loader signatures to accept `forceRefresh = false`.

- [ ] **Step 3: Refresh all visible detail data explicitly**

Change `handleRefresh`:

```ts
const handleRefresh = async () => {
  await Promise.all([
    loadDetail(true),
    loadInstHold(true),
    loadDividend(true),
    loadNews(true),
  ]);
};
```

- [ ] **Step 4: Preserve detail on refresh failure**

In `loadDetail`, only clear `detail` when `stockCode` is invalid. On fetch/cache error, set error but do not call `setDetail(null)`.

Use:

```ts
try {
  const data = await getStockDetail(stockCode, forceRefresh);
  setDetail(data);
} catch {
  if (!detail) setError(t.error.fetchStockDetail);
  else setError(t.error.fetchStockDetail);
}
```

Then remove the full-page error return when `detail` exists. Keep the full-page error only for `!detail`.

- [ ] **Step 5: Pass refresh options to secondary APIs**

Use:

```ts
const data = await getStockInstHold(stockCode, { forceRefresh });
const data = await getStockDividend(stockCode, { forceRefresh });
const data = await getStockNews(stockCode, { forceRefresh });
```

- [ ] **Step 6: Strategy expansion**

Keep expansion as an explicit user action. It may call:

```ts
const result = await getStrategyDetail(stockCode, strategyId);
```

Task 3 returns cached detail if present. If cache is missing, expansion is treated as an explicit user server action and may fetch strategy detail.

- [ ] **Step 7: Run verification**

Run: `npm test -- --run src/services/api.test.ts src/services/localDb.test.ts` from `frontend`

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/pages/StockDetailScreen.tsx
git commit -m "feat: render stock detail from cache on entry"
```

---

### Task 6: Make Login the Explicit Startup Screen

**Files:**
- Modify: `frontend/App.tsx`

**Interfaces:**
- Produces: `Screen` includes `'login'`.
- Produces: app startup waits for storage initialization before auth routing.
- Produces: unauthenticated state starts at and returns to login.

- [ ] **Step 1: Write routing expectations**

If component testing is practical, add `frontend/App.test.tsx` with React Native test utilities. If adding a renderer is too much for this change, use TypeScript compile plus manual verification after implementation. The key assertions are:

```ts
// startup before init: loading state visible
// unauthenticated after init: LoginScreen visible
// logout: currentScreen becomes login
```

- [ ] **Step 2: Add explicit login screen type and storage-ready state**

In `App.tsx`, change:

```ts
type Screen = 'login' | 'home' | 'settings' | 'login-settings' | 'profile' | 'stock-detail' | 'terms' | 'privacy';
const [isStorageReady, setIsStorageReady] = useState(false);
const [currentScreen, setCurrentScreen] = useState<Screen>('login');
```

- [ ] **Step 3: Set route after storage init**

Update init effect:

```ts
useEffect(() => {
  (async () => {
    try {
      await initStorage();
    } finally {
      const loggedIn = checkLoggedIn();
      setIsLoggedIn(loggedIn);
      setCurrentScreen(loggedIn ? 'home' : 'login');
      setIsStorageReady(true);
    }
  })();
}, []);
```

- [ ] **Step 4: Add loading state**

Before auth branches:

```tsx
if (!isStorageReady) {
  return (
    <I18nProvider>
      <SafeAreaView style={styles.safeArea}>
        <StatusBar style="dark" />
        <View style={styles.loadingShell}>
          <Text style={styles.subtleText}>Loading...</Text>
        </View>
      </SafeAreaView>
    </I18nProvider>
  );
}
```

Add `loadingShell` style with centered content.

- [ ] **Step 5: Route logout to login**

Change `handleLogout`:

```ts
const handleLogout = () => {
  clearAuthToken();
  setIsLoggedIn(false);
  setCurrentScreen('login');
  setScreenParams({});
};
```

Change unauthenticated back handlers from `home` to `login`:

```ts
onBack={() => setCurrentScreen('login')}
```

and legal back:

```ts
setCurrentScreen('login');
```

- [ ] **Step 6: Route login success to home**

Keep:

```ts
setIsLoggedIn(true);
setCurrentScreen('home');
```

Also clear screen params.

- [ ] **Step 7: Run TypeScript verification**

Run: `npx tsc --noEmit` from `frontend`

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add frontend/App.tsx
git commit -m "feat: start unauthenticated app at login"
```

---

### Task 7: End-to-End Verification

**Files:**
- No required edits unless verification reveals issues.

**Interfaces:**
- Verifies all tasks together.

- [ ] **Step 1: Run full frontend checks**

Run from `frontend`:

```bash
npm test -- --run
npx tsc --noEmit
```

Expected: both PASS.

- [ ] **Step 2: Start app**

Run from `frontend`:

```bash
npm run web
```

Expected: Expo web server starts.

- [ ] **Step 3: Manual offline-first checks**

In browser or device:

- Clear auth and open app: login page appears first.
- Log in with server available.
- Refresh stock list/detail once to populate cache.
- Stop backend server.
- Reload app while still authenticated: home page renders cached list.
- Open stock detail: cached detail sections render.
- Click refresh while backend is stopped: cached data remains visible and an error appears.
- Log out: login page appears.

- [ ] **Step 4: Commit verification fixes only if needed**

If any verification fix is needed:

```bash
git add <fixed-files>
git commit -m "fix: stabilize offline cache flow"
```

---

## Self-Review

- Spec coverage:
  - Explicit login first is covered by Task 6.
  - Native/web cache persistence is covered by Task 2.
  - Cache-first API reads and refresh-only server fetches are covered by Task 3.
  - Home cached data flow is covered by Task 4.
  - Detail cached data flow and secondary sections are covered by Task 5.
  - Verification is covered by Task 7.

- Placeholder scan:
  - No unresolved markers or unnamed implementation placeholders remain.
  - Task 6 allows manual verification only if adding a component renderer would expand scope; TypeScript and manual verification still gate completion.

- Type consistency:
  - `ReadOptions` is consistently `{ forceRefresh?: boolean }`.
  - Existing `getStockDetail(code, forceRefresh)` shape is preserved.
  - New secondary-section API methods use `(code, options?)`.
