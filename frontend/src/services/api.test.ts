import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { DividendRecord, InstHoldRecord, StockDetail, StockNews, StockSummary, StrategyDetail, WatchlistInsights } from '../types';

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

const strategyDetail: StrategyDetail = {
  strategy: {
    id: 'trend',
    name: 'Trend',
    period: '30d',
    return_rate: 5,
    max_drawdown: 2,
    win_rate: 60,
    risk: 'medium',
    summary: 'ok',
  },
  annualized_return: 12,
  sharpe_ratio: 1.1,
  trade_count: 2,
  rules: ['buy'],
  trades: [],
};

const detailWithStrategy: StockDetail = {
  ...detail,
  strategies: [strategyDetail.strategy],
};

const watchlistInsights: WatchlistInsights = {
  total: 1,
  groups: {
    positive: [stock],
    watch: [],
    cautious: [],
    insufficient_data: [],
  },
  risk_overview: '当前自选股未发现集中高风险提示，仍需结合仓位和估值检查。',
  data_updated_at: '2026-06-29T00:00:00Z',
  disclaimer: '仅供学习和分析参考，不构成投资建议。',
  data_health_overview: {
    total: 1,
    insufficient_count: 0,
    incomplete_count: 0,
    latest_updated_at: '2026-07-09T10:00:00',
    message: '当前自选股数据健康状况可用于基础参考。',
  },
  intelligence: {
    radar: {
      title: '自选股机会雷达',
      summary: '今日自选股中有 1 只可重点观察，仍需结合详情页依据。',
      priority_count: 1,
      cautious_count: 0,
      insufficient_count: 0,
      average_score: 80,
    },
    observations: [
      {
        type: 'priority',
        title: '优先复查重点观察股',
        description: '这些自选股的支撑因素相对更集中，建议先查看详情页确认依据。',
        stock_codes: ['600519'],
      },
    ],
    insights: [
      {
        code: '600519',
        name: '贵州茅台',
        focus_level: 'priority',
        focus_label: '重点观察',
        focus_reason: '支撑因素相对更集中，可优先查看详情页确认依据。',
        support_points: ['评分较高'],
        risk_points: [],
        data_completeness: 'complete',
        score: 80,
        risk_score: 0,
        priority_score: 45,
        updated_at: '2026-07-09T10:00:00',
      },
    ],
    sort_modes: ['overall', 'risk', 'data_health', 'recent_change'],
  },
};

const dividend: DividendRecord[] = [{
  ts_code: stock.code,
  ann_date: '20260601',
  div_proc: 'implemented',
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

function mockStorage() {
  vi.doMock('./storage', () => ({
    getApiBaseUrl: () => 'http://server.test',
    getAuthToken: () => 'token',
    savePasswordForOffline: vi.fn(),
    verifyOfflineLogin: vi.fn(async () => true),
    setOfflineToken: vi.fn(),
    setStoredUser: vi.fn(),
    setAuthToken: vi.fn(),
  }));
}

function mockLocalDb(overrides: Partial<typeof import('./localDb')> = {}) {
  vi.doMock('./localDb', () => ({
    getStocks: vi.fn(async () => null),
    saveStocks: vi.fn(),
    getSearchResult: vi.fn(async () => null),
    saveSearchResult: vi.fn(),
    getStockDetail: vi.fn(async () => null),
    saveStockDetail: vi.fn(),
    getStrategyDetail: vi.fn(async () => null),
    saveStrategyDetail: vi.fn(),
    getDividend: vi.fn(async () => null),
    saveDividend: vi.fn(),
    getNews: vi.fn(async () => null),
    saveNews: vi.fn(),
    getInstHold: vi.fn(async () => null),
    saveInstHold: vi.fn(),
    clearAllCache: vi.fn(),
    clearStockCache: vi.fn(),
    ...overrides,
  }));
}

describe('api cache policy', () => {
  beforeEach(() => {
    vi.resetModules();
    vi.clearAllMocks();
    vi.unstubAllGlobals();
    mockStorage();
  });

  it('returns an empty stock list without fetching when cache is missing', async () => {
    mockLocalDb();
    const fetchSpy = vi.fn();
    vi.stubGlobal('fetch', fetchSpy);
    const { getStocks } = await import('./api');

    await expect(getStocks()).resolves.toEqual({ data: [], fromCache: true });
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it('fetches and caches stock detail when cache is missing', async () => {
    const saveStockDetail = vi.fn();
    mockLocalDb({
      saveStockDetail,
    });
    const fetchSpy = vi.fn(async (url: string) => {
      if (url.endsWith(`/api/stocks/${stock.code}`)) {
        return { ok: true, status: 200, json: async () => detail };
      }
      return { ok: false, status: 404, json: async () => ({}) };
    });
    vi.stubGlobal('fetch', fetchSpy);
    const { getStockDetail } = await import('./api');

    await expect(getStockDetail(stock.code)).resolves.toEqual({ data: detail, fromCache: false });
    expect(saveStockDetail).toHaveBeenCalledWith(stock.code, detail);
  });

  it('returns empty secondary sections without fetching when cache is missing', async () => {
    mockLocalDb();
    const fetchSpy = vi.fn();
    vi.stubGlobal('fetch', fetchSpy);
    const { getStockDividend, getStockNews, getStockInstHold } = await import('./api');

    await expect(getStockDividend(stock.code)).resolves.toEqual({ data: [], fromCache: true });
    await expect(getStockNews(stock.code)).resolves.toEqual({ data: [], fromCache: true });
    await expect(getStockInstHold(stock.code)).resolves.toEqual({ data: [], fromCache: true });
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it('returns cached detail sections without fetching', async () => {
    mockLocalDb({
      getStockDetail: vi.fn(async () => detail),
      getStrategyDetail: vi.fn(async () => strategyDetail),
      getDividend: vi.fn(async () => dividend),
      getNews: vi.fn(async () => news),
      getInstHold: vi.fn(async () => instHold),
    });
    const fetchSpy = vi.fn();
    vi.stubGlobal('fetch', fetchSpy);
    const { getStockDetail, getStrategyDetail, getStockDividend, getStockNews, getStockInstHold } = await import('./api');

    await expect(getStockDetail(stock.code)).resolves.toEqual({ data: detail, fromCache: true });
    await expect(getStrategyDetail(stock.code, 'trend')).resolves.toEqual({ data: strategyDetail, fromCache: true });
    await expect(getStockDividend(stock.code)).resolves.toEqual({ data: dividend, fromCache: true });
    await expect(getStockNews(stock.code)).resolves.toEqual({ data: news, fromCache: true });
    await expect(getStockInstHold(stock.code)).resolves.toEqual({ data: instHold, fromCache: true });
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it('search falls back to cached search results when the server fails', async () => {
    mockLocalDb({
      getSearchResult: vi.fn(async () => [stock]),
    });
    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: false, json: async () => ({}) })));
    const { searchStocks } = await import('./api');

    await expect(searchStocks('ping')).resolves.toEqual({
      data: [stock],
      fromCache: true,
      isOffline: false,
    });
  });

  it('fetches watchlist insights with auth headers', async () => {
    mockLocalDb();
    const fetchSpy = vi.fn(async (url: string) => {
      if (url.endsWith('/api/watchlist/insights')) {
        return { ok: true, json: async () => watchlistInsights };
      }
      return { ok: false, json: async () => ({}) };
    });
    vi.stubGlobal('fetch', fetchSpy);
    const { getWatchlistInsights } = await import('./api');

    const result = await getWatchlistInsights();
    expect(result).toEqual(watchlistInsights);
    expect(result.data_health_overview?.message).toBe('当前自选股数据健康状况可用于基础参考。');
    expect(result.intelligence?.radar.title).toBe('自选股机会雷达');
    expect(result.intelligence?.observations[0]?.type).toBe('priority');
    expect(result.intelligence?.insights[0]?.focus_level).toBe('priority');
    expect(fetchSpy).toHaveBeenCalledWith(
      'http://server.test/api/watchlist/insights',
      { headers: { Authorization: 'Bearer token' } },
    );
  });

  it('marks refresh as offline when React Native reports Network request failed', async () => {
    mockLocalDb({
      getStocks: vi.fn(async () => [stock]),
    });
    vi.stubGlobal('fetch', vi.fn(async () => {
      throw new TypeError('Network request failed');
    }));
    const { refreshAllStocks } = await import('./api');

    await expect(refreshAllStocks()).resolves.toEqual({
      data: [stock],
      error: 'Offline - showing cached data',
      isOffline: true,
    });
  });

  it('refreshing stock detail also caches strategy detail for offline viewing', async () => {
    const saveStrategyDetail = vi.fn();
    mockLocalDb({
      saveStrategyDetail,
    });
    const fetchSpy = vi.fn(async (url: string) => {
      if (url.endsWith(`/api/stocks/${stock.code}`)) {
        return { ok: true, json: async () => detailWithStrategy };
      }
      if (url.endsWith(`/api/stocks/${stock.code}/strategies/${strategyDetail.strategy.id}`)) {
        return { ok: true, json: async () => strategyDetail };
      }
      return { ok: false, json: async () => ({}) };
    });
    vi.stubGlobal('fetch', fetchSpy);
    const { getStockDetail } = await import('./api');

    await expect(getStockDetail(stock.code, true)).resolves.toEqual({ data: detailWithStrategy, fromCache: false });

    expect(fetchSpy).toHaveBeenCalledWith(
      `http://server.test/api/stocks/${stock.code}/strategies/${strategyDetail.strategy.id}`,
      { headers: { Authorization: 'Bearer token' } },
    );
    expect(saveStrategyDetail).toHaveBeenCalledWith(stock.code, strategyDetail.strategy.id, strategyDetail);
  });

  it('falls back to offline login when the backend request fails and local credentials match', async () => {
    vi.spyOn(console, 'warn').mockImplementation(() => {});
    vi.spyOn(console, 'error').mockImplementation(() => {});
    const setOfflineToken = vi.fn();
    const setAuthToken = vi.fn();
    const setStoredUser = vi.fn();
    vi.doMock('./storage', () => ({
      getApiBaseUrl: () => 'http://server.test',
      getAuthToken: () => null,
      verifyOfflineLogin: vi.fn(async () => true),
      setOfflineToken,
      setStoredUser,
      setAuthToken,
    }));
    mockLocalDb();
    vi.stubGlobal('fetch', vi.fn(async () => {
      throw new TypeError('Network request failed');
    }));
    const { login } = await import('./api');

    const result = await login('Test', 'Test@bcd!234');

    expect(result).toMatchObject({
      username: 'Test',
      role: 'user',
      isOffline: true,
    });
    expect(result.token).toMatch(/^offline_Test_/);
    expect(setOfflineToken).toHaveBeenCalledWith(result.token);
    expect(setAuthToken).toHaveBeenCalledWith(result.token);
    expect(setStoredUser).toHaveBeenCalledWith('Test');
  });

  it('falls back to offline login when the backend returns a service unavailable response', async () => {
    vi.spyOn(console, 'log').mockImplementation(() => {});
    vi.spyOn(console, 'warn').mockImplementation(() => {});
    vi.spyOn(console, 'error').mockImplementation(() => {});
    vi.doMock('./storage', () => ({
      getApiBaseUrl: () => 'http://server.test',
      getAuthToken: () => null,
      verifyOfflineLogin: vi.fn(async () => true),
      setOfflineToken: vi.fn(),
      setStoredUser: vi.fn(),
      setAuthToken: vi.fn(),
    }));
    mockLocalDb();
    vi.stubGlobal('fetch', vi.fn(async () => ({
      ok: false,
      status: 503,
      json: async () => ({ detail: 'Service unavailable' }),
    })));
    const { login } = await import('./api');

    await expect(login('Test', 'Test@bcd!234')).resolves.toMatchObject({
      username: 'Test',
      isOffline: true,
    });
  });

});
