import type { StockSummary, StockDetail } from '../types';

const DB_KEYS = {
  STOCKS: 'local_stocks',
  STOCK_DETAIL_PREFIX: 'local_stock_detail_',
  LAST_UPDATE: 'local_last_update',
};

export async function saveStocks(stocks: StockSummary[]): Promise<void> {
  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      window.localStorage.setItem(DB_KEYS.STOCKS, JSON.stringify(stocks));
      window.localStorage.setItem(DB_KEYS.LAST_UPDATE, Date.now().toString());
    }
  } catch (e) {
    console.warn('Failed to save stocks to local storage:', e);
  }
}

export async function getStocks(): Promise<StockSummary[] | null> {
  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      const stored = window.localStorage.getItem(DB_KEYS.STOCKS);
      if (stored) {
        return JSON.parse(stored) as StockSummary[];
      }
    }
    return null;
  } catch (e) {
    console.warn('Failed to get stocks from local storage:', e);
    return null;
  }
}

export async function saveStockDetail(code: string, detail: StockDetail): Promise<void> {
  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      window.localStorage.setItem(`${DB_KEYS.STOCK_DETAIL_PREFIX}${code}`, JSON.stringify(detail));
    }
  } catch (e) {
    console.warn(`Failed to save stock detail ${code} to local storage:`, e);
  }
}

export async function getStockDetail(code: string): Promise<StockDetail | null> {
  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      const stored = window.localStorage.getItem(`${DB_KEYS.STOCK_DETAIL_PREFIX}${code}`);
      if (stored) {
        return JSON.parse(stored) as StockDetail;
      }
    }
    return null;
  } catch (e) {
    console.warn(`Failed to get stock detail ${code} from local storage:`, e);
    return null;
  }
}

export async function getLastUpdateTime(): Promise<number | null> {
  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      const stored = window.localStorage.getItem(DB_KEYS.LAST_UPDATE);
      if (stored) {
        return parseInt(stored, 10);
      }
    }
    return null;
  } catch (e) {
    console.warn('Failed to get last update time:', e);
    return null;
  }
}

export async function clearLocalData(): Promise<void> {
  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      const keys = Object.keys(window.localStorage);
      const dbKeys = keys.filter(key => 
        key === DB_KEYS.STOCKS || 
        key === DB_KEYS.LAST_UPDATE || 
        key.startsWith(DB_KEYS.STOCK_DETAIL_PREFIX)
      );
      dbKeys.forEach(key => window.localStorage.removeItem(key));
    }
  } catch (e) {
    console.warn('Failed to clear local data:', e);
  }
}
