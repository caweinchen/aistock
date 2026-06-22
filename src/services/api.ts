import { Platform } from 'react-native';
import type {
  StockSummary,
  StockDetail,
  StrategyDetail,
  BacktestRequest,
  BacktestTrade,
  StrategyResult,
} from '../types';
import { getApiBaseUrl, getAuthToken } from './storage';
import { saveStocks, saveStockDetail, getStocks as getLocalStocks, getStockDetail as getLocalStockDetail } from './localDb';

function getApiBase(): string {
  if (Platform.OS === 'android') {
    const configUrl = getApiBaseUrl();
    // 如果是默认配置，使用 Android 模拟器特殊地址
    if (configUrl === 'http://127.0.0.1:8000') {
      return 'http://10.0.2.2:8000';
    }
    return configUrl;
  }
  return getApiBaseUrl();
}

function getAuthHeaders(): HeadersInit {
  const token = getAuthToken();
  if (token) {
    return { Authorization: `Bearer ${token}` };
  }
  return {};
}

const cache = new Map<string, { data: unknown; timestamp: number }>();
const CACHE_TTL = 5 * 60 * 1000;

function getCached<T>(key: string): T | null {
  const item = cache.get(key);
  if (!item) return null;
  if (Date.now() - item.timestamp > CACHE_TTL) {
    cache.delete(key);
    return null;
  }
  return item.data as T;
}

function setCached(key: string, data: unknown): void {
  cache.set(key, { data, timestamp: Date.now() });
}

export async function getStocks(): Promise<StockSummary[]> {
  const cached = getCached<StockSummary[]>('stocks');
  if (cached) return cached;

  try {
    const response = await fetch(`${getApiBase()}/api/stocks`, {
      headers: getAuthHeaders(),
    });
    if (!response.ok) throw new Error('fetchStocks');
    const data = await response.json();
    setCached('stocks', data);
    await saveStocks(data);
    return data;
  } catch (err) {
    console.warn('Failed to fetch stocks from server, falling back to local storage:', err);
    const localData = await getLocalStocks();
    if (localData) return localData;
    throw err;
  }
}

export async function searchStocks(keyword: string): Promise<StockSummary[]> {
  const url = keyword
    ? `${getApiBase()}/api/stocks/search?q=${encodeURIComponent(keyword)}`
    : `${getApiBase()}/api/stocks`;
  const response = await fetch(url, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) throw new Error('searchStocks');
  return response.json();
}

export async function getStockDetail(code: string, forceRefresh = false): Promise<StockDetail> {
  if (!forceRefresh) {
    const cached = getCached<StockDetail>(`stock:${code}`);
    if (cached) return cached;
  } else {
    cache.delete(`stock:${code}`);
  }

  try {
    const response = await fetch(`${getApiBase()}/api/stocks/${code}`, {
      headers: getAuthHeaders(),
    });
    if (!response.ok) throw new Error('fetchStockDetail');
    const data = await response.json();
    setCached(`stock:${code}`, data);
    await saveStockDetail(code, data);
    return data;
  } catch (err) {
    console.warn(`Failed to fetch stock detail ${code} from server, falling back to local storage:`, err);
    const localData = await getLocalStockDetail(code);
    if (localData) return localData;
    throw err;
  }
}

export async function addToWatchlist(code: string): Promise<StockSummary[]> {
  const response = await fetch(`${getApiBase()}/api/watchlist/${code}`, {
    method: 'POST',
    headers: getAuthHeaders(),
  });
  if (!response.ok) throw new Error('addWatchlist');
  const data = await response.json();
  setCached('stocks', data);
  return data;
}

export async function removeFromWatchlist(code: string): Promise<StockSummary[]> {
  const response = await fetch(`${getApiBase()}/api/watchlist/${code}`, {
    method: 'DELETE',
    headers: getAuthHeaders(),
  });
  if (!response.ok) throw new Error('removeWatchlist');
  const data = await response.json();
  setCached('stocks', data);
  return data;
}

export async function getStrategyDetail(code: string, strategyId: string): Promise<StrategyDetail> {
  const cached = getCached<StrategyDetail>(`strategy:${code}:${strategyId}`);
  if (cached) return cached;

  const response = await fetch(`${getApiBase()}/api/stocks/${code}/strategies/${strategyId}`, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) throw new Error('fetchStrategy');
  const data = await response.json();
  setCached(`strategy:${code}:${strategyId}`, data);
  return data;
}

export async function getStockDividend(code: string): Promise<DividendRecord[]> {
  const response = await fetch(`${getApiBase()}/api/stocks/${code}/dividend`, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) throw new Error('fetchDividend');
  return response.json();
}

export async function getStockNews(code: string): Promise<StockNews[]> {
  const response = await fetch(`${getApiBase()}/api/stocks/${code}/news`, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) throw new Error('fetchNews');
  return response.json();
}

export async function getStockInstHold(code: string): Promise<InstHoldRecord[]> {
  const response = await fetch(`${getApiBase()}/api/stocks/${code}/inst-hold`, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) throw new Error('fetchInstHold');
  return response.json();
}

export async function createBacktest(request: BacktestRequest): Promise<StrategyDetail> {
  const response = await fetch(`${getApiBase()}/api/backtests`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify(request),
  });
  if (!response.ok) throw new Error('createBacktest');
  return response.json();
}

export async function login(username: string, password: string): Promise<{ token: string; username: string }> {
  let encryptedPassword = password;
  try {
    const { encryptPassword } = await import('../utils/crypto');
    encryptedPassword = await encryptPassword(password);
  } catch (e) {
    console.warn('Failed to encrypt password, sending as plain text:', e);
  }
  
  const response = await fetch(`${getApiBase()}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password: encryptedPassword }),
  });
  if (!response.ok) throw new Error('login');
  return response.json();
}

export async function refreshAllStocks(): Promise<StockSummary[]> {
  const response = await fetch(`${getApiBase()}/api/stocks/refresh-all`, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) throw new Error('refreshAllStocks');
  const data = await response.json();
  setCached('stocks', data);
  await saveStocks(data);
  return data;
}

export function clearCache(): void {
  cache.clear();
}