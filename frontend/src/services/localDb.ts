/**
 * localDb.ts - Typed cache for app data
 * 
 * Supports native AsyncStorage and web localStorage.
 * Provides save/get helpers for:
 * - stock list
 * - stock search result by normalized query
 * - stock detail by code
 * - strategy detail by stock code and strategy id
 * - dividend records by stock code
 * - news by stock code
 * - institutions holdings by stock code
 * - last update timestamps
 */

import { getStoredUser, getUserId, storage } from './storage';
import type { StockSummary, StockDetail, StrategyDetail, DividendRecord, StockNews, InstHoldRecord } from '../types';

// Cache key prefixes
const CACHE_PREFIX = 'db_';
const KEYS = {
  STOCKS: 'stocks',
  STOCK_DETAIL_PREFIX: 'stock_detail_',
  STRATEGY_DETAIL_PREFIX: 'strategy_detail_',
  DIVIDEND_PREFIX: 'dividend_',
  NEWS_PREFIX: 'news_',
  INST_HOLD_PREFIX: 'inst_hold_',
  SEARCH_PREFIX: 'search_',
  LAST_UPDATE: 'last_update',
};

function getCacheNamespace(): string {
  const userKey = getStoredUser() ?? getUserId() ?? 'anonymous';
  return `${CACHE_PREFIX}${encodeURIComponent(userKey)}_`;
}

function cacheKey(key: string): string {
  return `${getCacheNamespace()}${key}`;
}

// ============================================
// Stock List
// ============================================

export async function saveStocks(stocks: StockSummary[]): Promise<void> {
  try {
    await storage.setItem(cacheKey(KEYS.STOCKS), JSON.stringify(stocks));
    await storage.setItem(cacheKey(KEYS.LAST_UPDATE), Date.now().toString());
  } catch (e) {
    console.warn('Failed to save stocks to local storage:', e);
  }
}

export async function getStocks(): Promise<StockSummary[] | null> {
  try {
    const stored = await storage.getItem(cacheKey(KEYS.STOCKS));
    if (stored) {
      return JSON.parse(stored) as StockSummary[];
    }
    return null;
  } catch (e) {
    console.warn('Failed to get stocks from local storage:', e);
    return null;
  }
}

// ============================================
// Stock Detail
// ============================================

export async function saveStockDetail(code: string, detail: StockDetail): Promise<void> {
  try {
    await storage.setItem(cacheKey(`${KEYS.STOCK_DETAIL_PREFIX}${code}`), JSON.stringify(detail));
  } catch (e) {
    console.warn(`Failed to save stock detail ${code} to local storage:`, e);
  }
}

export async function getStockDetail(code: string): Promise<StockDetail | null> {
  try {
    const stored = await storage.getItem(cacheKey(`${KEYS.STOCK_DETAIL_PREFIX}${code}`));
    if (stored) {
      return JSON.parse(stored) as StockDetail;
    }
    return null;
  } catch (e) {
    console.warn(`Failed to get stock detail ${code} from local storage:`, e);
    return null;
  }
}

// ============================================
// Strategy Detail
// ============================================

export async function saveStrategyDetail(code: string, strategyId: string, detail: StrategyDetail): Promise<void> {
  try {
    await storage.setItem(cacheKey(`${KEYS.STRATEGY_DETAIL_PREFIX}${code}_${strategyId}`), JSON.stringify(detail));
  } catch (e) {
    console.warn(`Failed to save strategy detail ${code}_${strategyId} to local storage:`, e);
  }
}

export async function getStrategyDetail(code: string, strategyId: string): Promise<StrategyDetail | null> {
  try {
    const stored = await storage.getItem(cacheKey(`${KEYS.STRATEGY_DETAIL_PREFIX}${code}_${strategyId}`));
    if (stored) {
      return JSON.parse(stored) as StrategyDetail;
    }
    return null;
  } catch (e) {
    console.warn(`Failed to get strategy detail ${code}_${strategyId} from local storage:`, e);
    return null;
  }
}

// ============================================
// Dividend Records
// ============================================

export async function saveDividend(code: string, dividends: DividendRecord[]): Promise<void> {
  try {
    await storage.setItem(cacheKey(`${KEYS.DIVIDEND_PREFIX}${code}`), JSON.stringify(dividends));
  } catch (e) {
    console.warn(`Failed to save dividend ${code} to local storage:`, e);
  }
}

export async function getDividend(code: string): Promise<DividendRecord[] | null> {
  try {
    const stored = await storage.getItem(cacheKey(`${KEYS.DIVIDEND_PREFIX}${code}`));
    if (stored) {
      return JSON.parse(stored) as DividendRecord[];
    }
    return null;
  } catch (e) {
    console.warn(`Failed to get dividend ${code} from local storage:`, e);
    return null;
  }
}

// ============================================
// News
// ============================================

export async function saveNews(code: string, news: StockNews[]): Promise<void> {
  try {
    await storage.setItem(cacheKey(`${KEYS.NEWS_PREFIX}${code}`), JSON.stringify(news));
  } catch (e) {
    console.warn(`Failed to save news ${code} to local storage:`, e);
  }
}

export async function getNews(code: string): Promise<StockNews[] | null> {
  try {
    const stored = await storage.getItem(cacheKey(`${KEYS.NEWS_PREFIX}${code}`));
    if (stored) {
      return JSON.parse(stored) as StockNews[];
    }
    return null;
  } catch (e) {
    console.warn(`Failed to get news ${code} from local storage:`, e);
    return null;
  }
}

// ============================================
// Institution Holdings
// ============================================

export async function saveInstHold(code: string, holds: InstHoldRecord[]): Promise<void> {
  try {
    await storage.setItem(cacheKey(`${KEYS.INST_HOLD_PREFIX}${code}`), JSON.stringify(holds));
  } catch (e) {
    console.warn(`Failed to save institution holdings ${code} to local storage:`, e);
  }
}

export async function getInstHold(code: string): Promise<InstHoldRecord[] | null> {
  try {
    const stored = await storage.getItem(cacheKey(`${KEYS.INST_HOLD_PREFIX}${code}`));
    if (stored) {
      return JSON.parse(stored) as InstHoldRecord[];
    }
    return null;
  } catch (e) {
    console.warn(`Failed to get institution holdings ${code} from local storage:`, e);
    return null;
  }
}

// ============================================
// Search Results
// ============================================

export async function saveSearchResult(query: string, results: StockSummary[]): Promise<void> {
  try {
    const normalizedQuery = query.toLowerCase().trim();
    await storage.setItem(cacheKey(`${KEYS.SEARCH_PREFIX}${normalizedQuery}`), JSON.stringify(results));
  } catch (e) {
    console.warn('Failed to save search result to local storage:', e);
  }
}

export async function getSearchResult(query: string): Promise<StockSummary[] | null> {
  try {
    const normalizedQuery = query.toLowerCase().trim();
    const stored = await storage.getItem(cacheKey(`${KEYS.SEARCH_PREFIX}${normalizedQuery}`));
    if (stored) {
      return JSON.parse(stored) as StockSummary[];
    }
    return null;
  } catch (e) {
    console.warn('Failed to get search result from local storage:', e);
    return null;
  }
}

// ============================================
// Last Update Timestamp
// ============================================

export async function getLastUpdateTime(): Promise<number | null> {
  try {
    const stored = await storage.getItem(cacheKey(KEYS.LAST_UPDATE));
    if (stored) {
      return parseInt(stored, 10);
    }
    return null;
  } catch (e) {
    console.warn('Failed to get last update time:', e);
    return null;
  }
}

export async function setLastUpdateTime(timestamp: number): Promise<void> {
  try {
    await storage.setItem(cacheKey(KEYS.LAST_UPDATE), timestamp.toString());
  } catch (e) {
    console.warn('Failed to set last update time:', e);
  }
}

// ============================================
// Clear All Cache
// ============================================

export async function clearAllCache(): Promise<void> {
  try {
    const allKeys = await storage.getAllKeys();
    const cacheKeys = allKeys.filter((key: string) => key.startsWith(CACHE_PREFIX));
    if (cacheKeys.length > 0) {
      await storage.multiRemove(cacheKeys);
    }
  } catch (e) {
    console.warn('Failed to clear cache:', e);
  }
}

export async function clearStockCache(code: string): Promise<void> {
  try {
    await storage.multiRemove([
      cacheKey(`${KEYS.STOCK_DETAIL_PREFIX}${code}`),
      cacheKey(`${KEYS.DIVIDEND_PREFIX}${code}`),
      cacheKey(`${KEYS.NEWS_PREFIX}${code}`),
      cacheKey(`${KEYS.INST_HOLD_PREFIX}${code}`),
    ]);
    // Also clear strategy details for this stock
    // Note: We'd need to enumerate keys to clear all strategy details for this stock
  } catch (e) {
    console.warn('Failed to clear stock cache:', e);
  }
}

// ============================================
// Check if cache exists
// ============================================

export async function hasCachedStocks(): Promise<boolean> {
  const stocks = await getStocks();
  return stocks !== null && stocks.length > 0;
}

export async function hasCachedStockDetail(code: string): Promise<boolean> {
  const detail = await getStockDetail(code);
  return detail !== null;
}
