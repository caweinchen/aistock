import { Platform } from 'react-native';
import type {
  StockSummary,
  StockDetail,
  StrategyDetail,
  BacktestRequest,
  BacktestTrade,
  StrategyResult,
} from '../types';
import { getApiBaseUrl } from './storage';

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

  const response = await fetch(`${getApiBase()}/api/stocks`);
  if (!response.ok) throw new Error('fetchStocks');
  const data = await response.json();
  setCached('stocks', data);
  return data;
}

export async function searchStocks(keyword: string): Promise<StockSummary[]> {
  const url = keyword
    ? `${getApiBase()}/api/stocks/search?q=${encodeURIComponent(keyword)}`
    : `${getApiBase()}/api/stocks`;
  const response = await fetch(url);
  if (!response.ok) throw new Error('searchStocks');
  return response.json();
}

export async function getStockDetail(code: string): Promise<StockDetail> {
  const cached = getCached<StockDetail>(`stock:${code}`);
  if (cached) return cached;

  const response = await fetch(`${getApiBase()}/api/stocks/${code}`);
  if (!response.ok) throw new Error('fetchStockDetail');
  const data = await response.json();
  setCached(`stock:${code}`, data);
  return data;
}

export async function addToWatchlist(code: string): Promise<StockSummary[]> {
  const response = await fetch(`${getApiBase()}/api/watchlist/${code}`, { method: 'POST' });
  if (!response.ok) throw new Error('addWatchlist');
  const data = await response.json();
  setCached('stocks', data);
  return data;
}

export async function removeFromWatchlist(code: string): Promise<StockSummary[]> {
  const response = await fetch(`${getApiBase()}/api/watchlist/${code}`, { method: 'DELETE' });
  if (!response.ok) throw new Error('removeWatchlist');
  const data = await response.json();
  setCached('stocks', data);
  return data;
}

export async function getStrategyDetail(code: string, strategyId: string): Promise<StrategyDetail> {
  const cached = getCached<StrategyDetail>(`strategy:${code}:${strategyId}`);
  if (cached) return cached;

  const response = await fetch(`${getApiBase()}/api/stocks/${code}/strategies/${strategyId}`);
  if (!response.ok) throw new Error('fetchStrategy');
  const data = await response.json();
  setCached(`strategy:${code}:${strategyId}`, data);
  return data;
}

export async function createBacktest(request: BacktestRequest): Promise<StrategyDetail> {
  const response = await fetch(`${getApiBase()}/api/backtests`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  if (!response.ok) throw new Error('createBacktest');
  return response.json();
}

export async function login(username: string, password: string): Promise<{ token: string; username: string }> {
  const response = await fetch(`${getApiBase()}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  if (!response.ok) throw new Error('login');
  return response.json();
}

export function clearCache(): void {
  cache.clear();
}