import { useCallback, useEffect, useRef, useState } from 'react';
import type { StockSummary, StockDetail, StrategyDetail, StrategyResult, BacktestRequest } from '../types';
import { getStocks, searchStocks, getStockDetail, addToWatchlist, removeFromWatchlist, getStrategyDetail, createBacktest, refreshAllStocks } from '../services/api';
import { useTranslation } from '../i18n';
import { checkNetwork, isNetworkFailure } from '../services/network';

export function useStockData() {
  const { t } = useTranslation();
  const [stocks, setStocks] = useState<StockSummary[]>([]);
  const [selectedCode, setSelectedCode] = useState<string | null>(null);
  const [detail, setDetail] = useState<StockDetail | null>(null);
  const [isLoadingStocks, setIsLoadingStocks] = useState(true);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fromCache, setFromCache] = useState(false);
  const [isOffline, setIsOffline] = useState(false);
  const [offlineNoCache, setOfflineNoCache] = useState(false);
  const [watchlistCodes, setWatchlistCodes] = useState<Set<string>>(new Set());
  const [customStrategiesByCode, setCustomStrategiesByCode] = useState<Record<string, StrategyResult[]>>({});
  const [tokenInvalid, setTokenInvalid] = useState(false);
  const detailCacheRef = useRef<Record<string, StockDetail>>({});
  const strategyDetailCacheRef = useRef<Record<string, StrategyDetail>>({});
  const selectedCodeRef = useRef<string | null>(null);

  const loadStocksFromCache = useCallback(async () => {
    setIsLoadingStocks(true);
    setError(null);
    setOfflineNoCache(false);

    try {
      const networkStatus = await checkNetwork();
      const cachedResult = await getStocks(false);
      const backendOffline = networkStatus !== 'online';

      if (cachedResult.data && cachedResult.data.length > 0) {
        setStocks(cachedResult.data);
        setWatchlistCodes(new Set(cachedResult.data.map((stock) => stock.code)));
        setFromCache(true);
        setIsOffline(backendOffline || (cachedResult.isOffline ?? false));

        if (!selectedCodeRef.current && cachedResult.data.length > 0) {
          await loadStockDetail(cachedResult.data[0].code);
        } else if (selectedCodeRef.current) {
          const exists = cachedResult.data.find(s => s.code === selectedCodeRef.current);
          if (exists) {
            await loadStockDetail(selectedCodeRef.current);
          } else if (cachedResult.data.length > 0) {
            await loadStockDetail(cachedResult.data[0].code);
          }
        }
      } else if (backendOffline) {
        setStocks([]);
        setWatchlistCodes(new Set());
        setFromCache(false);
        setOfflineNoCache(true);
        setIsOffline(backendOffline);
      } else {
        const onlineResult = await getStocks(true);
        const data = onlineResult.data ?? [];
        setStocks(data);
        setWatchlistCodes(new Set(data.map((stock) => stock.code)));
        setFromCache(false);
        setOfflineNoCache(data.length === 0);
        setIsOffline(false);

        if (!selectedCodeRef.current && data.length > 0) {
          await loadStockDetail(data[0].code);
        }
      }
    } catch (err) {
      setStocks([]);
      setWatchlistCodes(new Set());
      const isNetworkError = isNetworkFailure(err);
      setOfflineNoCache(isNetworkError);
      setIsOffline(isNetworkError);
      const errorKey = err instanceof Error ? err.message : 'fetchStocks';
      setError(t.error[errorKey as keyof typeof t.error] || t.error.fetchStocks);
    } finally {
      setIsLoadingStocks(false);
    }
  }, [t]);

  const refreshWatchlist = useCallback(async () => {
    setIsLoadingStocks(true);
    setError(null);
    setTokenInvalid(false);
    setOfflineNoCache(false);

    try {
      const result = await refreshAllStocks();

      if (result.tokenInvalid) {
        setTokenInvalid(true);
        setIsLoadingStocks(false);
        return;
      }

      const payload = result.data || [];
      setStocks(payload);
      setWatchlistCodes(new Set(payload.map((stock) => stock.code)));
      setFromCache(false);
      setIsOffline(false);

      if (result.error) {
        setError(result.error);
        setIsOffline((current) => result.isOffline ?? current);
      }

      if (selectedCodeRef.current) {
        await loadStockDetail(selectedCodeRef.current, true);
      }
    } catch (err) {
      const errorKey = err instanceof Error ? err.message : 'refreshAllStocks';
      setError(t.error[errorKey as keyof typeof t.error] || t.error.refreshAllStocks);
      const isNetworkError = isNetworkFailure(err);
      setIsOffline(isNetworkError);
    } finally {
      setIsLoadingStocks(false);
    }
  }, [t]);

  const loadStocks = useCallback(async (query = '') => {
    setIsLoadingStocks(true);
    setError(null);
    setOfflineNoCache(false);

    try {
      if (query) {
        const result = await searchStocks(query);
        setStocks(result.data);
        setFromCache(result.fromCache);
        setIsOffline((current) => result.isOffline ?? current);
      } else {
        try {
          const result = await getStocks(true);
          const data = result.data ?? [];
          setStocks(data);
          setWatchlistCodes(new Set(data.map((stock) => stock.code)));
          setFromCache(false);
          setIsOffline(false);

          if (!selectedCodeRef.current && data.length > 0) {
            await loadStockDetail(data[0].code);
          }
        } catch (serverErr) {
          console.log('Server connection failed during refresh, falling back to cache:', serverErr);
          const cachedResult = await getStocks(false);
          const data = cachedResult.data ?? [];
          setStocks(data);
          setWatchlistCodes(new Set(data.map((stock) => stock.code)));
          setFromCache(true);
          setIsOffline(true);

          if (!selectedCodeRef.current && data.length > 0) {
            await loadStockDetail(data[0].code);
          }
        }
      }
    } catch (err) {
      const errorKey = err instanceof Error ? err.message : 'fetchStocks';
      setError(t.error[errorKey as keyof typeof t.error] || t.error.fetchStocks);
      const isNetworkError = isNetworkFailure(err);
      setIsOffline(isNetworkError);
    } finally {
      setIsLoadingStocks(false);
    }
  }, [t]);

  const loadStockDetail = useCallback(async (code: string, forceRefresh = false) => {
    selectedCodeRef.current = code;
    setSelectedCode(code);

    const cachedDetail = detailCacheRef.current[code];

    if (cachedDetail && !forceRefresh) {
      setDetail(cachedDetail);
      setFromCache(true);
    }

    setIsLoadingDetail(!cachedDetail || forceRefresh);
    setError(null);

    try {
      const result = await getStockDetail(code, forceRefresh);
      const payload = result.data;

      if (payload) {
        detailCacheRef.current[code] = payload;
        if (selectedCodeRef.current === code) {
          setDetail(payload);
          setFromCache(result.fromCache);
          setIsOffline((current) => result.isOffline ?? current);
        }
      }
    } catch (err) {
      if (!cachedDetail || forceRefresh) {
        const errorKey = err instanceof Error ? err.message : 'fetchStockDetail';
        setError(t.error[errorKey as keyof typeof t.error] || t.error.fetchStockDetail);
        const isNetworkError = isNetworkFailure(err);
        setIsOffline(isNetworkError);
      }
    } finally {
      if (selectedCodeRef.current === code) {
        setIsLoadingDetail(false);
      }
    }
  }, [t]);

  const toggleWatchlist = useCallback(async (stock: StockSummary): Promise<StockSummary[] | null> => {
    const isInWatchlist = watchlistCodes.has(stock.code);
    setError(null);

    try {
      const payload = isInWatchlist
        ? await removeFromWatchlist(stock.code)
        : await addToWatchlist(stock.code);

      setStocks(payload);
      setWatchlistCodes(new Set(payload.map((item) => item.code)));
      setFromCache(false);
      setIsOffline(false);

      if (!isInWatchlist) {
        await loadStockDetail(stock.code, true);
        return payload;
      }

      if (!payload.find((item) => item.code === selectedCode)) {
        if (payload[0]) {
          await loadStockDetail(payload[0].code);
        } else {
          selectedCodeRef.current = null;
          setSelectedCode(null);
          setDetail(null);
        }
      }

      return payload;
    } catch (err) {
      const errorKey = err instanceof Error ? err.message : 'addWatchlist';
      setError(t.error[errorKey as keyof typeof t.error] || t.error.addWatchlist);
      return null;
    }
  }, [loadStockDetail, selectedCode, watchlistCodes, t]);

  const loadStrategyDetail = useCallback(async (strategyId: string): Promise<StrategyDetail | undefined> => {
    if (!selectedCode) return undefined;

    // 浣跨敤绛栫暐璇︽儏缂撳瓨
    const cacheKey = `${selectedCode}:${strategyId}`;
    const cached = strategyDetailCacheRef.current[cacheKey];
    if (cached) return cached;

    try {
      const result = await getStrategyDetail(selectedCode, strategyId);
      const strategyDetail = result.data;
      if (!strategyDetail) return undefined;

      strategyDetailCacheRef.current[cacheKey] = strategyDetail;
      return strategyDetail;
    } catch (err) {
      const errorKey = err instanceof Error ? err.message : 'fetchStrategy';
      setError(t.error[errorKey as keyof typeof t.error] || t.error.fetchStrategy);
      return undefined;
    }
  }, [selectedCode, t]);

  const createCustomBacktest = useCallback(async (request: BacktestRequest): Promise<StrategyDetail | undefined> => {
    setError(null);
    try {
      const payload = await createBacktest(request);
      setCustomStrategiesByCode((current) => {
        const existing = current[request.code] ?? [];
        const next = existing.filter((s) => s.id !== payload.strategy.id);
        return { ...current, [request.code]: [...next, payload.strategy] };
      });
      return payload;
    } catch (err) {
      const errorKey = err instanceof Error ? err.message : 'createBacktest';
      setError(t.error[errorKey as keyof typeof t.error] || t.error.createBacktest);
      return undefined;
    }
  }, [t]);

  useEffect(() => {
    void loadStocksFromCache();
  }, [loadStocksFromCache]);

  return {
    stocks,
    selectedCode,
    detail,
    isLoadingStocks,
    isLoadingDetail,
    error,
    fromCache,
    isOffline,
    offlineNoCache,
    tokenInvalid,
    watchlistCodes,
    customStrategiesByCode,
    loadStocks,
    loadStocksFromCache,
    loadStockDetail,
    toggleWatchlist,
    loadStrategyDetail,
    createCustomBacktest,
    refreshWatchlist,
    setError,
  };
}
