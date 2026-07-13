import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { AlertTriangle, ChevronRight, RefreshCcw } from 'lucide-react-native';
import { StockRow } from '../components/StockRow';
import { WatchlistInsightsPanel } from '../components/WatchlistInsightsPanel';
import { FactorTile } from '../components/FactorTile';
import { StrategyCard } from '../components/StrategyCard';
import { AlertCard } from '../components/AlertCard';
import { PriceChart } from '../components/PriceChart';
import { BacktestBuilder } from '../components/BacktestBuilder';
import { useStockData } from '../hooks/useStockData';
import { getWatchlistInsights } from '../services/api';
import { formatPrice, formatUpdatedAt, getChangeColor } from '../utils/formatters';
import type { ResearchSnapshot, StrategyTemplate, WatchlistInsights } from '../types';
import { useEffect, useState } from 'react';
import { useTranslation } from '../i18n';

interface HomeScreenProps {
  onOpenSettings?: () => void;
  onOpenProfile?: () => void;
  onLogout?: () => void;
  onOpenStockDetail?: (stockCode: string) => void;
  onTokenInvalid?: () => void;
  pendingSearchQuery?: string | null;
  selectedStockCode?: string;
  onSelectedStockCodeChange?: (stockCode: string) => void;
  onResearchSnapshotChange?: (snapshot: ResearchSnapshot) => void;
  onOfflineChange?: (isOffline: boolean) => void;
  onWatchlistUpdated?: () => void;
}

export function HomeScreen({
  onOpenStockDetail,
  onTokenInvalid,
  pendingSearchQuery = null,
  selectedStockCode,
  onSelectedStockCodeChange,
  onResearchSnapshotChange,
  onOfflineChange,
  onWatchlistUpdated,
}: HomeScreenProps) {
  const { t, locale } = useTranslation();
  const {
    stocks,
    selectedCode,
    detail,
    isLoadingStocks,
    isLoadingDetail,
    error,
    isOffline,
    offlineNoCache,
    tokenInvalid,
    watchlistCodes,
    customStrategiesByCode,
    loadStocks,
    loadStockDetail,
    toggleWatchlist,
    loadStrategyDetail,
    createCustomBacktest,
    refreshWatchlist,
  } = useStockData();

  useEffect(() => {
    if (tokenInvalid && onTokenInvalid) {
      onTokenInvalid();
    }
  }, [tokenInvalid, onTokenInvalid]);

  useEffect(() => {
    if (onOfflineChange) {
      onOfflineChange(isOffline);
    }
  }, [isOffline, onOfflineChange]);

  const [updatingWatchlistCode, setUpdatingWatchlistCode] = useState<string | null>(null);
  const [expandedStrategyId, setExpandedStrategyId] = useState<string | null>(null);
  const [loadingStrategyId, setLoadingStrategyId] = useState<string | null>(null);
  const [strategyDetails, setStrategyDetails] = useState<Record<string, unknown>>({});
  const [isBuilderOpen, setIsBuilderOpen] = useState(false);
  const [backtestName, setBacktestName] = useState(t.home.myStrategy);
  const [backtestTemplate, setBacktestTemplate] = useState<StrategyTemplate>('trend-breakout');
  const [lookbackDays, setLookbackDays] = useState(180);
  const [isCreatingBacktest, setIsCreatingBacktest] = useState(false);
  const [isRefreshingWatchlist, setIsRefreshingWatchlist] = useState(false);
  const [watchlistInsights, setWatchlistInsights] = useState<WatchlistInsights | null>(null);
  const [isLoadingInsights, setIsLoadingInsights] = useState(false);
  const [insightsError, setInsightsError] = useState(false);

  useEffect(() => {
    if (pendingSearchQuery !== null) {
      void loadStocks(pendingSearchQuery);
    }
  }, [pendingSearchQuery, loadStocks]);

  useEffect(() => {
    if (selectedStockCode) {
      void loadStockDetail(selectedStockCode);
    }
  }, [selectedStockCode, loadStockDetail]);

  const activeSelectedCode = selectedStockCode ?? selectedCode;
  const selectedStock =
    detail?.stock.code === activeSelectedCode
      ? detail.stock
      : stocks.find((stock) => stock.code === activeSelectedCode) ?? detail?.stock ?? stocks[0];
  const marketScore = selectedStock?.score ?? 0;
  const alertCount = detail?.alerts.length ?? 0;
  
  const averageWinRate = detail?.strategies.length
    ? Math.round(detail.strategies.reduce((sum, s) => sum + s.win_rate, 0) / detail.strategies.length)
    : 0;

  useEffect(() => {
    if (!selectedStock) return;
    onResearchSnapshotChange?.({
      stockName: selectedStock.name,
      stockCode: selectedStock.code,
      score: selectedStock.score,
      alertCount,
      averageWinRate,
      aiSummary: detail?.ai_summary,
      dataStatus: detail?.data_status,
    });
  }, [selectedStock, detail, alertCount, averageWinRate, onResearchSnapshotChange]);

  const displayedStrategies = selectedCode
    ? [...(detail?.strategies ?? []), ...(customStrategiesByCode[selectedCode] ?? [])]
    : [];

  const handleLoadStrategyDetail = async (strategyId: string) => {
    if (!selectedCode) return;
    
    if (expandedStrategyId === strategyId) {
      setExpandedStrategyId(null);
      return;
    }
    
    setExpandedStrategyId(strategyId);
    setLoadingStrategyId(strategyId);
    
    const result = await loadStrategyDetail(strategyId);
    
    if (result) {
      const key = `${selectedCode}:${strategyId}`;
      setStrategyDetails((current) => ({ ...current, [key]: result }));
    }
    setLoadingStrategyId(null);
  };

  const handleCreateBacktest = async () => {
    if (!selectedCode) return;
    setIsCreatingBacktest(true);
    const result = await createCustomBacktest({
      code: selectedCode,
      name: backtestName,
      template: backtestTemplate,
      lookback_days: lookbackDays,
      risk: backtestTemplate === 'dividend-defense' ? 'low' : 'medium',
    });
    if (result) {
      const cacheKey = `${selectedCode}:${result.strategy.id}`;
      setStrategyDetails((current) => ({ ...current, [cacheKey]: result }));
      setExpandedStrategyId(result.strategy.id);
      setIsBuilderOpen(false);
    }
    setIsCreatingBacktest(false);
  };

  const handleToggleWatchlist = async (stock: typeof stocks[0]) => {
    setUpdatingWatchlistCode(stock.code);
    const updated = await toggleWatchlist(stock);
    setUpdatingWatchlistCode(null);

    if (updated && onWatchlistUpdated) {
      onWatchlistUpdated();
    }
    if (updated) {
      void loadWatchlistInsights();
    }
  };

  const loadWatchlistInsights = async () => {
    setIsLoadingInsights(true);
    setInsightsError(false);
    try {
      const insights = await getWatchlistInsights();
      setWatchlistInsights(insights);
    } catch {
      setInsightsError(true);
    } finally {
      setIsLoadingInsights(false);
    }
  };

  useEffect(() => {
    if (stocks.length) {
      void loadWatchlistInsights();
    } else {
      setWatchlistInsights(null);
    }
  }, [stocks.length]);

  const handleRefreshWatchlist = async () => {
    setIsRefreshingWatchlist(true);
    await refreshWatchlist();
    await loadWatchlistInsights();
    setIsRefreshingWatchlist(false);
  };

  const handleStockPress = (stockCode: string) => {
    onSelectedStockCodeChange?.(stockCode);
    if (onOpenStockDetail) {
      onOpenStockDetail(stockCode);
    } else {
      void loadStockDetail(stockCode);
    }
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
      {offlineNoCache && (
        <View style={styles.offlinePanel}>
          <View style={styles.offlineIcon}>
            <AlertTriangle size={24} color="#F59E0B" />
          </View>
          <View style={styles.offlineCopy}>
            <Text style={styles.offlineTitle}>{t.home.offlineMode}</Text>
            <Text style={styles.offlineText}>{t.home.noCachedData}</Text>
            <Pressable style={styles.offlineRetryButton} onPress={handleRefreshWatchlist}>
              <RefreshCcw size={16} color="#FFFFFF" />
              <Text style={styles.offlineRetryButtonText}>{t.home.connectAndRefresh}</Text>
            </Pressable>
          </View>
        </View>
      )}
      {error && (
        <View style={styles.errorPanel}>
          <AlertTriangle size={20} color="#B42318" />
          <View style={styles.errorCopy}>
            <Text style={styles.errorTitle}>{t.home.dataLoadFailed}</Text>
            <Text style={styles.errorText}>{error}</Text>
            <Pressable style={styles.retryButton} onPress={() => void loadStocks(pendingSearchQuery ?? '')}>
              <RefreshCcw size={16} color="#FFFFFF" />
              <Text style={styles.retryButtonText}>{t.home.retry}</Text>
            </Pressable>
          </View>
        </View>
      )}
      <View style={styles.sectionHeader}>
        <Text style={styles.sectionTitle}>{t.stock.watchlist}</Text>
        <Pressable style={styles.textButton} onPress={handleRefreshWatchlist}>
          {isRefreshingWatchlist ? (
            <ActivityIndicator size="small" color="#0F8B8D" />
          ) : (
            <>
              <Text style={styles.textButtonLabel}>{t.common.refresh}</Text>
              <RefreshCcw size={15} color="#0F8B8D" />
            </>
          )}
        </Pressable>
      </View>

      <WatchlistInsightsPanel
        error={insightsError}
        insights={watchlistInsights}
        loading={isLoadingInsights}
        locale={locale}
        onOpenStock={handleStockPress}
        onRefresh={() => void loadWatchlistInsights()}
        onRetry={() => void loadWatchlistInsights()}
      />

      <View style={styles.stockList}>
        {stocks.map((stock) => (
          <StockRow
            key={stock.code}
            isInWatchlist={watchlistCodes.has(stock.code)}
            isSelected={stock.code === activeSelectedCode}
            isUpdatingWatchlist={updatingWatchlistCode === stock.code}
            stock={stock}
            onPress={() => handleStockPress(stock.code)}
            onToggleWatchlist={() => handleToggleWatchlist(stock)}
          />
        ))}
        {!stocks.length && !isLoadingStocks && <Text style={styles.emptyText}>{t.home.noStocks}</Text>}
      </View>

      {selectedStock && !onOpenStockDetail && (
        <View style={styles.currentPanel}>
          <View style={styles.currentHeader}>
            <View>
              <Text style={styles.currentName}>{selectedStock.name}</Text>
              <Text style={styles.stockCode}>{selectedStock.code}</Text>
            </View>
            <View style={styles.currentPriceBlock}>
              <Text style={styles.stockPrice}>{formatPrice(selectedStock.price)}</Text>
              <Text style={[styles.stockChange, { color: getChangeColor(selectedStock.change_percent) }]}>
                {selectedStock.change_percent >= 0 ? '+' : ''}{selectedStock.change_percent.toFixed(2)}%
              </Text>
            </View>
          </View>
          <Text style={styles.currentSummary}>
            {detail?.ai_summary ?? t.home.aiSummaryDefault}
          </Text>
        </View>
      )}

      {selectedStock && !onOpenStockDetail && detail?.history?.length && <PriceChart stock={selectedStock} history={detail.history} />}

      {!onOpenStockDetail && (
        <>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>{t.factor.title}</Text>
            <Text style={styles.subtleText}>{selectedStock?.name ?? t.home.notSelected}</Text>
          </View>
          <View style={styles.factorGrid}>
            {isLoadingDetail && <LoadingBlock label={t.home.loadingDetail} />}
            {detail?.factors.map((factor) => <FactorTile key={factor.key} factor={factor} />)}
          </View>

          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>{t.strategy.title}</Text>
            <Pressable style={styles.textButton} onPress={() => setIsBuilderOpen((v) => !v)}>
              <Text style={styles.textButtonLabel}>{t.backtest.title}</Text>
              <ChevronRight size={16} color="#0F8B8D" />
            </Pressable>
          </View>
          {isBuilderOpen && (
            <BacktestBuilder
              isCreating={isCreatingBacktest}
              lookbackDays={lookbackDays}
              name={backtestName}
              template={backtestTemplate}
              onChangeLookbackDays={setLookbackDays}
              onChangeName={setBacktestName}
              onChangeTemplate={setBacktestTemplate}
              onCreate={handleCreateBacktest}
            />
          )}
          {displayedStrategies.map((strategy) => (
            <StrategyCard
              key={strategy.id}
              detail={selectedCode ? (strategyDetails[`${selectedCode}:${strategy.id}`] as never) : undefined}
              isExpanded={expandedStrategyId === strategy.id}
              isLoading={loadingStrategyId === strategy.id}
              strategy={strategy}
              onPress={() => handleLoadStrategyDetail(strategy.id)}
            />
          ))}

          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>{t.home.riskAlertSection}</Text>
            <Text style={styles.subtleText}>{detail?.updated_at ? formatUpdatedAt(detail.updated_at, locale === 'zh' ? 'zh-CN' : locale === 'zh-Hant' ? 'zh-TW' : 'en-US', t.formatter.updated) : ''}</Text>
          </View>
          {detail?.alerts.length ? (
            detail.alerts.map((alert) => <AlertCard key={`${alert.level}-${alert.title}`} alert={alert} />)
          ) : (
            <View style={styles.warningPanel}>
              <View style={styles.warningIcon}>
                <AlertTriangle size={20} color="#B45309" />
              </View>
              <View style={styles.warningCopy}>
                <Text style={styles.warningTitle}>{t.home.warningTitle}</Text>
                <Text style={styles.warningText}>{t.home.warningText}</Text>
              </View>
            </View>
          )}
        </>
      )}
    </ScrollView>
  );
}

function LoadingBlock({ label }: { label: string }) {
  return (
    <View style={styles.loadingBlock}>
      <ActivityIndicator color="#0F8B8D" />
      <Text style={styles.subtleText}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  content: { padding: 20, paddingBottom: 36, gap: 18 },
  subtleText: { color: '#6B7280', fontSize: 13 },
  errorPanel: {
    backgroundColor: '#FEF3F2',
    borderColor: '#FDA29B',
    borderRadius: 8,
    borderWidth: 1,
    flexDirection: 'row',
    gap: 12,
    padding: 14,
  },
  errorCopy: { flex: 1, gap: 8 },
  errorTitle: { color: '#B42318', fontSize: 14, fontWeight: '800' },
  errorText: { color: '#912018', fontSize: 13, lineHeight: 20 },
  retryButton: {
    alignItems: 'center',
    alignSelf: 'flex-start',
    backgroundColor: '#B42318',
    borderRadius: 8,
    flexDirection: 'row',
    gap: 6,
    minHeight: 34,
    paddingHorizontal: 12,
  },
  retryButtonText: { color: '#FFFFFF', fontSize: 13, fontWeight: '800' },
  sectionHeader: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between', marginTop: 4 },
  sectionTitle: { color: '#162033', fontSize: 20, fontWeight: '800' },
  textButton: { alignItems: 'center', flexDirection: 'row', gap: 5, minHeight: 36 },
  textButtonLabel: { color: '#0F8B8D', fontSize: 14, fontWeight: '700' },
  stockList: {
    backgroundColor: '#FFFFFF',
    borderColor: '#E5E7EB',
    borderRadius: 8,
    borderWidth: 1,
    overflow: 'hidden',
  },
  insightPanel: {
    backgroundColor: '#FFFFFF',
    borderColor: '#D8DEE9',
    borderRadius: 8,
    borderWidth: 1,
    gap: 12,
    padding: 16,
  },
  insightHeader: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between', gap: 12 },
  dataHealthStrip: {
    backgroundColor: '#F8FAFC',
    borderColor: '#E5E7EB',
    borderRadius: 8,
    borderWidth: 1,
    gap: 6,
    padding: 12,
  },
  dataHealthTitle: {
    color: '#162033',
    fontSize: 13,
    fontWeight: '700',
  },
  watchlistRadarCard: {
    backgroundColor: '#F8FAFC',
    borderColor: '#D1D5DB',
    borderRadius: 8,
    borderWidth: 1,
    gap: 8,
    padding: 12,
  },
  radarStatsRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  radarStatText: {
    backgroundColor: '#FFFFFF',
    borderColor: '#E5E7EB',
    borderRadius: 8,
    borderWidth: 1,
    color: '#374151',
    fontSize: 12,
    fontWeight: '700',
    paddingHorizontal: 8,
    paddingVertical: 5,
  },
  observationBlock: {
    gap: 8,
  },
  observationItem: {
    backgroundColor: '#FFFFFF',
    borderColor: '#E5E7EB',
    borderRadius: 8,
    borderWidth: 1,
    gap: 6,
    padding: 12,
  },
  insightGroup: { gap: 8 },
  insightGroupTitle: { color: '#162033', fontSize: 14, fontWeight: '800' },
  insightItem: {
    backgroundColor: '#F8FAFC',
    borderColor: '#E5E7EB',
    borderRadius: 8,
    borderWidth: 1,
    gap: 4,
    padding: 10,
  },
  insightName: { color: '#162033', fontSize: 14, fontWeight: '800' },
  insightReason: { color: '#4B5563', fontSize: 12, lineHeight: 18 },
  insightEmpty: { color: '#9CA3AF', fontSize: 12 },
  disclaimerText: { color: '#6B7280', fontSize: 12, lineHeight: 18 },
  emptyText: { color: '#6B7280', padding: 16 },
  currentPanel: {
    backgroundColor: '#FFFFFF',
    borderColor: '#D8DEE9',
    borderRadius: 8,
    borderWidth: 1,
    gap: 12,
    padding: 16,
  },
  currentHeader: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between', gap: 12 },
  currentName: { color: '#162033', fontSize: 18, fontWeight: '800' },
  stockCode: { color: '#6B7280', fontSize: 12 },
  currentPriceBlock: { alignItems: 'flex-end', gap: 4 },
  stockPrice: { color: '#162033', fontSize: 16, fontWeight: '700' },
  stockChange: { fontSize: 12, fontWeight: '700' },
  currentSummary: { color: '#4B5563', fontSize: 13, lineHeight: 21 },
  factorGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  loadingBlock: {
    alignItems: 'center',
    backgroundColor: '#FFFFFF',
    borderColor: '#E5E7EB',
    borderRadius: 8,
    borderWidth: 1,
    flexBasis: '100%',
    flexDirection: 'row',
    gap: 10,
    minHeight: 62,
    padding: 14,
  },
  warningPanel: {
    backgroundColor: '#FFF7ED',
    borderColor: '#FED7AA',
    borderRadius: 8,
    borderWidth: 1,
    flexDirection: 'row',
    gap: 12,
    padding: 14,
  },
  warningIcon: {
    alignItems: 'center',
    backgroundColor: '#FFEDD5',
    borderRadius: 8,
    height: 38,
    justifyContent: 'center',
    width: 38,
  },
  warningCopy: { flex: 1, gap: 5 },
  warningTitle: { color: '#92400E', fontSize: 14, fontWeight: '800' },
  warningText: { color: '#9A3412', fontSize: 13, lineHeight: 20 },
  offlinePanel: {
    backgroundColor: '#FFFBEB',
    borderColor: '#FEF3C7',
    borderRadius: 8,
    borderWidth: 1,
    flexDirection: 'row',
    gap: 12,
    padding: 14,
  },
  offlineIcon: {
    alignItems: 'center',
    backgroundColor: '#FEF3C7',
    borderRadius: 8,
    height: 44,
    justifyContent: 'center',
    width: 44,
  },
  offlineCopy: { flex: 1, gap: 5 },
  offlineTitle: { color: '#92400E', fontSize: 14, fontWeight: '800' },
  offlineText: { color: '#B45309', fontSize: 13, lineHeight: 20 },
  offlineRetryButton: {
    alignItems: 'center',
    backgroundColor: '#F59E0B',
    borderRadius: 8,
    flexDirection: 'row',
    gap: 6,
    minHeight: 34,
    paddingHorizontal: 12,
  },
  offlineRetryButtonText: { color: '#FFFFFF', fontSize: 13, fontWeight: '800' },
});
