/**
 * api.ts - Server calls and cache policy
 * 
 * Normal read methods return cached data without fetching.
 * Refresh methods (or calls with forceRefresh: true) fetch from server, write cache, and return fresh data.
 * If a refresh fails, the method returns cached data when available and surfaces error info for UI.
 */

import type {
  StockSummary,
  StockDetail,
  StrategyDetail,
  BacktestRequest,
  DividendRecord,
  StockNews,
  InstHoldRecord,
} from '../types';
import { getApiBaseUrl, getAuthToken } from './storage';
import * as localDb from './localDb';
import { isOnline, isOffline, checkNetwork } from './network';

function getApiBase(): string {
  return getApiBaseUrl();
}

function getAuthHeaders(): HeadersInit {
  const token = getAuthToken();
  if (token) {
    return { Authorization: `Bearer ${token}` };
  }
  return {};
}

export function debugAuthToken(): string | null {
  return getAuthToken();
}

// ============================================
// Stock List - Cache First
// ============================================

export async function getStocks(forceRefresh = false): Promise<{ data: StockSummary[] | null; fromCache: boolean; error?: string; isOffline?: boolean }> {
  if (!forceRefresh && isOffline()) {
    const cached = await localDb.getStocks();
    return { data: cached ?? [], fromCache: true, isOffline: true };
  }

  try {
    const response = await fetch(`${getApiBase()}/api/stocks`, {
      headers: getAuthHeaders(),
    });
    if (!response.ok) throw new Error('fetchStocks');
    const data: StockSummary[] = await response.json();
    
    await localDb.saveStocks(data);
    return { data, fromCache: false, isOffline: false };
  } catch (err) {
    const cached = await localDb.getStocks();
    if (cached && cached.length > 0) {
      const isNetworkError = err instanceof TypeError && err.message.includes('fetch');
      return { data: cached, fromCache: true, error: isNetworkError ? 'Offline - showing cached data' : 'Server error - showing cached data', isOffline: isNetworkError };
    }
    throw err;
  }
}

// ============================================
// Search - Explicit Server Action
// ============================================

export async function searchStocks(keyword: string): Promise<{ data: StockSummary[]; fromCache: boolean; isOffline?: boolean }> {
  const url = keyword
    ? `${getApiBase()}/api/stocks/search?q=${encodeURIComponent(keyword)}`
    : `${getApiBase()}/api/stocks`;

  if (isOffline()) {
    if (keyword) {
      const cachedSearch = await localDb.getSearchResult(keyword);
      if (cachedSearch) {
        return { data: cachedSearch, fromCache: true, isOffline: true };
      }
    }
    const cachedStocks = await localDb.getStocks();
    if (cachedStocks) {
      return { data: cachedStocks, fromCache: true, isOffline: true };
    }
    throw new Error('searchStocksOffline');
  }

  try {
    const response = await fetch(url, {
      headers: getAuthHeaders(),
    });
    if (!response.ok) throw new Error('searchStocks');
    const data: StockSummary[] = await response.json();

    if (keyword) {
      await localDb.saveSearchResult(keyword, data);
    } else {
      await localDb.saveStocks(data);
    }
    return { data, fromCache: false, isOffline: false };
  } catch (err) {
    const isNetworkError = err instanceof TypeError && err.message.includes('fetch');
    if (keyword) {
      const cachedSearch = await localDb.getSearchResult(keyword);
      if (cachedSearch) {
        return { data: cachedSearch, fromCache: true, isOffline: isNetworkError };
      }
    }
    const cachedStocks = await localDb.getStocks();
    if (cachedStocks) {
      return { data: cachedStocks, fromCache: true, isOffline: isNetworkError };
    }
    throw err;
  }
}

// ============================================
// Stock Detail - Cache First
// ============================================

export async function getStockDetail(code: string, forceRefresh = false): Promise<{ data: StockDetail | null; fromCache: boolean; error?: string; tokenInvalid?: boolean; isOffline?: boolean }> {
  if (!forceRefresh && isOffline()) {
    const cached = await localDb.getStockDetail(code);
    return { data: cached, fromCache: true, isOffline: true };
  }

  try {
    const response = await fetch(`${getApiBase()}/api/stocks/${code}`, {
      headers: getAuthHeaders(),
    });
    
    if (response.status === 401) {
      return { data: null, fromCache: false, tokenInvalid: true, isOffline: false };
    }
    
    if (!response.ok) throw new Error('fetchStockDetail');
    const data: StockDetail = await response.json();
    
    await localDb.saveStockDetail(code, data);
    return { data, fromCache: false, isOffline: false };
  } catch (err) {
    const cached = await localDb.getStockDetail(code);
    if (cached) {
      const isNetworkError = err instanceof TypeError && err.message.includes('fetch');
      return { data: cached, fromCache: true, error: isNetworkError ? 'Offline - showing cached data' : 'Server error - showing cached data', isOffline: isNetworkError };
    }
    throw err;
  }
}

// ============================================
// Watchlist - Server Actions
// ============================================

export async function addToWatchlist(code: string): Promise<StockSummary[]> {
  const response = await fetch(`${getApiBase()}/api/watchlist/${code}`, {
    method: 'POST',
    headers: getAuthHeaders(),
  });
  if (!response.ok) throw new Error('addWatchlist');
  const data: StockSummary[] = await response.json();
  
  // Update cache
  await localDb.saveStocks(data);
  return data;
}

export async function removeFromWatchlist(code: string): Promise<StockSummary[]> {
  const response = await fetch(`${getApiBase()}/api/watchlist/${code}`, {
    method: 'DELETE',
    headers: getAuthHeaders(),
  });
  if (!response.ok) throw new Error('removeWatchlist');
  const data: StockSummary[] = await response.json();
  
  // Update cache
  await localDb.saveStocks(data);
  return data;
}

// ============================================
// Strategy Detail - Cache First
// ============================================

export async function getStrategyDetail(code: string, strategyId: string, forceRefresh = false): Promise<{ data: StrategyDetail | null; fromCache: boolean; error?: string; isOffline?: boolean }> {
  if (!forceRefresh && isOffline()) {
    const cached = await localDb.getStrategyDetail(code, strategyId);
    return { data: cached, fromCache: true, isOffline: true };
  }

  try {
    const response = await fetch(`${getApiBase()}/api/stocks/${code}/strategies/${strategyId}`, {
      headers: getAuthHeaders(),
    });
    if (!response.ok) throw new Error('fetchStrategy');
    const data: StrategyDetail = await response.json();
    
    await localDb.saveStrategyDetail(code, strategyId, data);
    return { data, fromCache: false, isOffline: false };
  } catch (err) {
    const cached = await localDb.getStrategyDetail(code, strategyId);
    if (cached) {
      const isNetworkError = err instanceof TypeError && err.message.includes('fetch');
      return { data: cached, fromCache: true, error: isNetworkError ? 'Offline - showing cached data' : 'Server error - showing cached data', isOffline: isNetworkError };
    }
    throw err;
  }
}

// ============================================
// Dividend - Cache First
// ============================================

export async function getStockDividend(code: string, forceRefresh = false): Promise<{ data: DividendRecord[] | null; fromCache: boolean; error?: string; isOffline?: boolean }> {
  if (!forceRefresh && isOffline()) {
    const cached = await localDb.getDividend(code);
    return { data: cached ?? [], fromCache: true, isOffline: true };
  }

  try {
    const response = await fetch(`${getApiBase()}/api/stocks/${code}/dividend`, {
      headers: getAuthHeaders(),
    });
    if (!response.ok) throw new Error('fetchDividend');
    const data: DividendRecord[] = await response.json();
    
    await localDb.saveDividend(code, data);
    return { data, fromCache: false, isOffline: false };
  } catch (err) {
    const cached = await localDb.getDividend(code);
    if (cached) {
      const isNetworkError = err instanceof TypeError && err.message.includes('fetch');
      return { data: cached, fromCache: true, error: isNetworkError ? 'Offline - showing cached data' : 'Server error - showing cached data', isOffline: isNetworkError };
    }
    throw err;
  }
}

// ============================================
// News - Cache First
// ============================================

export async function getStockNews(code: string, forceRefresh = false): Promise<{ data: StockNews[] | null; fromCache: boolean; error?: string; isOffline?: boolean }> {
  if (!forceRefresh && isOffline()) {
    const cached = await localDb.getNews(code);
    return { data: cached ?? [], fromCache: true, isOffline: true };
  }

  try {
    const response = await fetch(`${getApiBase()}/api/stocks/${code}/news`, {
      headers: getAuthHeaders(),
    });
    if (!response.ok) throw new Error('fetchNews');
    const data: StockNews[] = await response.json();
    
    await localDb.saveNews(code, data);
    return { data, fromCache: false, isOffline: false };
  } catch (err) {
    const cached = await localDb.getNews(code);
    if (cached) {
      const isNetworkError = err instanceof TypeError && err.message.includes('fetch');
      return { data: cached, fromCache: true, error: isNetworkError ? 'Offline - showing cached data' : 'Server error - showing cached data', isOffline: isNetworkError };
    }
    throw err;
  }
}

// ============================================
// Institution Holdings - Cache First
// ============================================

export async function getStockInstHold(code: string, forceRefresh = false): Promise<{ data: InstHoldRecord[] | null; fromCache: boolean; error?: string; isOffline?: boolean }> {
  if (!forceRefresh && isOffline()) {
    const cached = await localDb.getInstHold(code);
    return { data: cached ?? [], fromCache: true, isOffline: true };
  }

  try {
    const response = await fetch(`${getApiBase()}/api/stocks/${code}/inst-hold`, {
      headers: getAuthHeaders(),
    });
    if (!response.ok) throw new Error('fetchInstHold');
    const data: InstHoldRecord[] = await response.json();
    
    await localDb.saveInstHold(code, data);
    return { data, fromCache: false, isOffline: false };
  } catch (err) {
    const cached = await localDb.getInstHold(code);
    if (cached) {
      const isNetworkError = err instanceof TypeError && err.message.includes('fetch');
      return { data: cached, fromCache: true, error: isNetworkError ? 'Offline - showing cached data' : 'Server error - showing cached data', isOffline: isNetworkError };
    }
    throw err;
  }
}

// ============================================
// Backtest - Explicit Server Action
// ============================================

export async function createBacktest(request: BacktestRequest): Promise<StrategyDetail> {
  const response = await fetch(`${getApiBase()}/api/backtests`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
    body: JSON.stringify(request),
  });
  if (!response.ok) throw new Error('createBacktest');
  return response.json();
}

// ============================================
// Login - Online First with Offline Fallback
// ============================================

export async function login(username: string, password: string): Promise<{ token: string; username: string; isOffline?: boolean }> {
  let encryptedPassword = password;
  try {
    const { encryptPassword } = await import('../utils/crypto');
    encryptedPassword = await encryptPassword(password);
    console.log('Password encrypted successfully, starting with:', encryptedPassword.substring(0, 30));
  } catch (e) {
    console.warn('Failed to encrypt password, sending as plain text:', e);
  }
  
  // Try online login first
  try {
    const response = await fetch(`${getApiBase()}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password: encryptedPassword }),
    });
    
    console.log('Login response status:', response.status);
    
    if (!response.ok) {
      const errorText = await response.text();
      console.error('Login failed:', response.status, errorText);
      throw new Error('login');
    }
    
    const result = await response.json();
    console.log('Login successful, token received');
    
    // Save password hash for offline login
    await import('./storage').then(({ savePasswordForOffline }) => savePasswordForOffline(username, password));
    
    return { token: result.token, username: result.username };
  } catch (err) {
    console.error('Login catch error:', err);
    // Check if it's a network error (offline)
    if (err instanceof TypeError && err.message.includes('fetch')) {
      // Try offline login
      const { verifyOfflineLogin, setOfflineToken, setStoredUser, setAuthToken } = await import('./storage');
      const isValid = await verifyOfflineLogin(username, password);
      
      if (isValid) {
        // Generate offline token
        const offlineToken = `offline_${username}_${Date.now()}`;
        setOfflineToken(offlineToken);
        setAuthToken(offlineToken);
        setStoredUser(username);
        return { token: offlineToken, username, isOffline: true };
      }
      
      throw new Error('offlineLoginFailed');
    }
    
    throw err;
  }
}

// ============================================
// Token Verification - Check if token is valid
// ============================================

export async function verifyToken(): Promise<{ valid: boolean; isOffline: boolean }> {
  try {
    const response = await fetch(`${getApiBase()}/api/auth/verify`, {
      headers: getAuthHeaders(),
    });
    
    if (response.ok) {
      return { valid: true, isOffline: false };
    }
    
    if (response.status === 401) {
      return { valid: false, isOffline: false };
    }
    
    return { valid: false, isOffline: false };
  } catch (err) {
    const isNetworkError = err instanceof TypeError && err.message.includes('fetch');
    return { valid: false, isOffline: isNetworkError };
  }
}

// ============================================
// Refresh All - Explicit Server Action
// ============================================

export async function refreshAllStocks(): Promise<{ data: StockSummary[] | null; error?: string; tokenInvalid?: boolean; isOffline?: boolean }> {
  try {
    const response = await fetch(`${getApiBase()}/api/stocks/refresh-all`, {
      headers: getAuthHeaders(),
    });
    
    if (response.status === 401) {
      return { data: null, tokenInvalid: true };
    }
    
    if (!response.ok) throw new Error('refreshAllStocks');
    const data: StockSummary[] = await response.json();
    
    await localDb.saveStocks(data);
    return { data };
  } catch (err) {
    const cached = await localDb.getStocks();
    if (cached && cached.length > 0) {
      const isNetworkError = err instanceof TypeError && err.message.includes('fetch');
      return { 
        data: cached, 
        error: isNetworkError ? 'Offline - showing cached data' : 'Server error - showing cached data',
        isOffline: isNetworkError
      };
    }
    throw err;
  }
}

// ============================================
// Clear Cache
// ============================================

export async function clearCache(): Promise<void> {
  await localDb.clearAllCache();
}

export async function clearStockCache(code: string): Promise<void> {
  await localDb.clearStockCache(code);
}
