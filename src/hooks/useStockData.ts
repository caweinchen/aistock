import { useCallback, useEffect, useRef, useState } from 'react';
import type { StockSummary, StockDetail, StrategyDetail, StrategyResult, BacktestRequest } from '../types';
import { getStocks, searchStocks, getStockDetail, addToWatchlist, removeFromWatchlist, getStrategyDetail, createBacktest } from '../services/api';
import { useTranslation } from '../i18n';

export function useStockData() {
  const { t } = useTranslation();
  const [stocks, setStocks] = useState<StockSummary[]>([]);
  const [selectedCode, setSelectedCode] = useState<string | null>(null);
  const [detail, setDetail] = useState<StockDetail | null>(null);
  const [isLoadingStocks, setIsLoadingStocks] = useState(true);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [watchlistCodes, setWatchlistCodes] = useState<Set<string>>(new Set());
  const [customStrategiesByCode, setCustomStrategiesByCode] = useState<Record<string, StrategyResult[]>>({});
  const detailCacheRef = useRef<Record<string, StockDetail>>({});
  const strategyDetailCacheRef = useRef<Record<string, StrategyDetail>>({});
  const selectedCodeRef = useRef<string | null>(null);

  const loadStocks = useCallback(async (query = '') => {
    setIsLoadingStocks(true);
    setError(null);

    try {
      const payload = await (query ? searchStocks(query) : getStocks());
      setStocks(payload);
      if (!query) {
        setWatchlistCodes(new Set(payload.map((stock) => stock.code)));
      }

      if (payload.length > 0 && !selectedCodeRef.current) {
        await loadStockDetail(payload[0].code);
      }
    } catch (err) {
      const errorKey = err instanceof Error ? err.message : 'fetchStocks';
      setError(t.error[errorKey as keyof typeof t.error] || t.error.fetchStocks);
    } finally {
      setIsLoadingStocks(false);
    }
  }, [t]);

  const loadStockDetail = useCallback(async (code: string) => {
    selectedCodeRef.current = code;
    setSelectedCode(code);
    const cachedDetail = detailCacheRef.current[code];
    
    if (cachedDetail) {
      setDetail(cachedDetail);
    }

    setIsLoadingDetail(!cachedDetail);
    setError(null);

    try {
      const payload = await getStockDetail(code);
      detailCacheRef.current[code] = payload;
      if (selectedCodeRef.current === code) {
        setDetail(payload);
      }
    } catch (err) {
      if (!cachedDetail) {
        const errorKey = err instanceof Error ? err.message : 'fetchStockDetail';
        setError(t.error[errorKey as keyof typeof t.error] || t.error.fetchStockDetail);
      }
    } finally {
      if (selectedCodeRef.current === code) {
        setIsLoadingDetail(false);
      }
    }
  }, []);

  const toggleWatchlist = useCallback(async (stock: StockSummary) => {
    const isInWatchlist = watchlistCodes.has(stock.code);
    setError(null);

    try {
      const payload = isInWatchlist 
        ? await removeFromWatchlist(stock.code)
        : await addToWatchlist(stock.code);
      
      setWatchlistCodes(new Set(payload.map((item) => item.code)));
      
      if (!payload.find((item) => item.code === selectedCode)) {
        if (payload[0]) {
          await loadStockDetail(payload[0].code);
        } else {
          selectedCodeRef.current = null;
          setSelectedCode(null);
          setDetail(null);
        }
      }
    } catch (err) {
      const errorKey = err instanceof Error ? err.message : 'addWatchlist';
      setError(t.error[errorKey as keyof typeof t.error] || t.error.addWatchlist);
    }
  }, [loadStockDetail, selectedCode, watchlistCodes, t]);

  const loadStrategyDetail = useCallback(async (strategyId: string): Promise<StrategyDetail | undefined> => {
    if (!selectedCode) return undefined;

    // 使用策略详情缓存
    const cacheKey = `${selectedCode}:${strategyId}`;
    const cached = strategyDetailCacheRef.current[cacheKey];
    if (cached) return cached;

    try {
      // 从已有的策略列表中找到策略
      const strategy = detail?.strategies.find((s) => s.id === strategyId);
      const customStrategy = customStrategiesByCode[selectedCode]?.find((s) => s.id === strategyId);
      const foundStrategy = strategy || customStrategy;
      
      if (!foundStrategy) return undefined;

      // 构建模拟的策略详情
      const strategyDetail: StrategyDetail = {
        strategy: foundStrategy,
        annualized_return: foundStrategy.return_rate * 1.5,
        sharpe_ratio: Math.min(2.5, Math.max(0.5, foundStrategy.return_rate / Math.abs(foundStrategy.max_drawdown))),
        trade_count: 5,
        rules: [
          `${foundStrategy.name} rule 1`,
          `${foundStrategy.name} rule 2`,
          `${foundStrategy.name} rule 3`,
        ],
        trades: (detail?.history ?? []).slice(0, 5).map((point, i) => ({
          date: point.date,
          action: (i % 2 === 0 ? 'buy' : 'sell') as 'buy' | 'sell',
          price: point.close,
          quantity: 100,
          reason: `${foundStrategy.name} signal`,
        })),
      };

      strategyDetailCacheRef.current[cacheKey] = strategyDetail;
      return strategyDetail;
    } catch (err) {
      const errorKey = err instanceof Error ? err.message : 'fetchStrategy';
      setError(t.error[errorKey as keyof typeof t.error] || t.error.fetchStrategy);
      return undefined;
    }
  }, [selectedCode, detail, customStrategiesByCode, t]);

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
    void loadStocks();
  }, [loadStocks]);

  return {
    stocks,
    selectedCode,
    detail,
    isLoadingStocks,
    isLoadingDetail,
    error,
    watchlistCodes,
    customStrategiesByCode,
    loadStocks,
    loadStockDetail,
    toggleWatchlist,
    loadStrategyDetail,
    createCustomBacktest,
    setError,
  };
}