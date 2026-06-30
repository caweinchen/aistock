import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { ArrowLeft, AlertTriangle, Sparkles, TrendingUp, TrendingDown, RefreshCcw } from 'lucide-react-native';
import { FactorTile } from '../components/FactorTile';
import { StrategyCard } from '../components/StrategyCard';
import { AlertCard } from '../components/AlertCard';
import { PriceChart } from '../components/PriceChart';
import type { ResearchSnapshot, StockDetail, StrategyDetail, InstHoldRecord, DividendRecord, StockNews } from '../types';
import { translateDividendPlan, translateInstType, translateNewsSource, useTranslation } from '../i18n';
import { formatPrice, formatPercent, getChangeColor, getScoreColor } from '../utils/formatters';
import { useState, useEffect } from 'react';
import { getStockDetail, getStrategyDetail, getStockInstHold, getStockDividend, getStockNews } from '../services/api';

interface StockDetailScreenProps {
  stockCode: string;
  onBack: () => void;
  onTokenInvalid?: () => void;
  researchSnapshot?: ResearchSnapshot | null;
  onResearchSnapshotChange?: (snapshot: ResearchSnapshot) => void;
}

export function StockDetailScreen({ stockCode, onBack, onTokenInvalid, researchSnapshot, onResearchSnapshotChange }: StockDetailScreenProps) {
  const { t } = useTranslation();
  const [detail, setDetail] = useState<StockDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [fromCache, setFromCache] = useState(false);
  const [isOffline, setIsOffline] = useState(false);
  const [offlineNoCache, setOfflineNoCache] = useState(false);
  const [expandedStrategyId, setExpandedStrategyId] = useState<string | null>(null);
  const [loadingStrategyId, setLoadingStrategyId] = useState<string | null>(null);
  const [strategyDetails, setStrategyDetails] = useState<Record<string, StrategyDetail>>({});
  const [instHold, setInstHold] = useState<InstHoldRecord[]>([]);
  const [instHoldLoading, setInstHoldLoading] = useState(false);
  const [dividend, setDividend] = useState<DividendRecord[]>([]);
  const [dividendLoading, setDividendLoading] = useState(false);
  const [news, setNews] = useState<StockNews[]>([]);
  const [newsLoading, setNewsLoading] = useState(false);

  // Cache-first loading on mount
  useEffect(() => {
    void loadDetail(false); // cache-first
    void loadInstHold(false); // cache-first
    void loadDividend(false); // cache-first
    void loadNews(false); // cache-first
  }, [stockCode]);

  useEffect(() => {
    if (!detail || !onResearchSnapshotChange) return;
    const averageWinRate = detail.strategies.length
      ? Math.round(detail.strategies.reduce((sum, strategy) => sum + strategy.win_rate, 0) / detail.strategies.length)
      : 0;

    onResearchSnapshotChange({
      stockName: detail.stock.name,
      stockCode: detail.stock.code,
      score: detail.stock.score,
      alertCount: detail.alerts.length,
      averageWinRate,
      aiSummary: detail.ai_summary,
      dataStatus: detail.data_status,
    });
  }, [detail, onResearchSnapshotChange]);

  const loadInstHold = async (forceRefresh = false) => {
    if (!stockCode) return;
    setInstHoldLoading(true);
    try {
      const result = await getStockInstHold(stockCode, forceRefresh);
      if (result.data) {
        setInstHold(result.data);
        setFromCache(result.fromCache);
      }
    } catch (err) {
      console.warn('Failed to load institution holdings:', err);
    } finally {
      setInstHoldLoading(false);
    }
  };

  const loadDividend = async (forceRefresh = false) => {
    if (!stockCode) return;
    setDividendLoading(true);
    try {
      const result = await getStockDividend(stockCode, forceRefresh);
      if (result.data) {
        setDividend(result.data);
        setFromCache(result.fromCache);
      }
    } catch (err) {
      console.warn('Failed to load dividend records:', err);
    } finally {
      setDividendLoading(false);
    }
  };

  const loadNews = async (forceRefresh = false) => {
    if (!stockCode) return;
    setNewsLoading(true);
    try {
      const result = await getStockNews(stockCode, forceRefresh);
      if (result.data) {
        setNews(result.data);
        setFromCache(result.fromCache);
      }
    } catch (err) {
      console.warn('Failed to load news:', err);
    } finally {
      setNewsLoading(false);
    }
  };

  const loadDetail = async (forceRefresh = false) => {
    if (!stockCode) {
      setError(t.error.invalidStockCode);
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    setError(null);
    setOfflineNoCache(false);
    try {
      const result = await getStockDetail(stockCode, forceRefresh);
      
      if (result.tokenInvalid && onTokenInvalid) {
        onTokenInvalid();
        return;
      }
      
      if (result.data) {
        setDetail(result.data);
        setFromCache(result.fromCache);
        setIsOffline(result.isOffline ?? false);
        if (result.error) {
          setError(result.error);
        }
      } else if (result.isOffline) {
        setOfflineNoCache(true);
        setIsOffline(true);
      }
    } catch (err) {
      setError(t.error.fetchStockDetail);
      const isNetworkError = err instanceof TypeError && err.message.includes('fetch');
      setIsOffline(isNetworkError);
    } finally {
      setIsLoading(false);
    }
  };

  const handleLoadStrategyDetail = async (strategyId: string) => {
    if (!stockCode) return;

    if (expandedStrategyId === strategyId) {
      setExpandedStrategyId(null);
      return;
    }

    setExpandedStrategyId(strategyId);
    setLoadingStrategyId(strategyId);

    try {
      // Cache-first: try to get cached strategy detail first
      const result = await getStrategyDetail(stockCode, strategyId, false);
      const key = `${stockCode}:${strategyId}`;
      const strategyDetail = result.data;
      if (strategyDetail) {
        setStrategyDetails((current) => ({ ...current, [key]: strategyDetail }));
      }
    } catch (err) {
      // Silently fail for strategy detail - user can retry
      console.warn('Failed to load strategy detail:', err);
    } finally {
      setLoadingStrategyId(null);
    }
  };

  // Explicit refresh - server fetch with cache update
  const handleRefresh = async () => {
    await Promise.all([
      loadDetail(true),
      loadInstHold(true),
      loadDividend(true),
      loadNews(true),
    ]);
  };

  if (isLoading) {
    return (
      <View style={styles.screenContainer}>
        <View style={styles.header}>
          <Pressable style={styles.backButton} onPress={onBack}>
            <ArrowLeft size={20} color="#162033" />
          </Pressable>
          <View style={styles.headerTitleBlock}>
            <Text style={styles.loadingTitle}>{t.home.loadingDetail}</Text>
          </View>
        </View>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#0F8B8D" />
          <Text style={styles.loadingText}>{t.home.loadingDetail}</Text>
        </View>
      </View>
    );
  }

  if (offlineNoCache) {
    return (
      <View style={styles.screenContainer}>
        <View style={styles.header}>
          <Pressable style={styles.backButton} onPress={onBack}>
            <ArrowLeft size={20} color="#162033" />
          </Pressable>
          <View style={styles.headerTitleBlock}>
            <Text style={styles.stockName}>{stockCode}</Text>
          </View>
        </View>
        <View style={styles.offlineContainer}>
          <AlertTriangle size={48} color="#F59E0B" />
          <Text style={styles.offlineTitle}>{t.home.offlineMode}</Text>
          <Text style={styles.offlineText}>{t.home.noCachedData}</Text>
          <Pressable style={styles.offlineRetryButton} onPress={handleRefresh}>
            <RefreshCcw size={16} color="#FFFFFF" />
            <Text style={styles.offlineRetryButtonText}>{t.home.connectAndRefresh}</Text>
          </Pressable>
        </View>
      </View>
    );
  }

  if (error || !detail) {
    return (
      <View style={styles.screenContainer}>
        <View style={styles.header}>
          <Pressable style={styles.backButton} onPress={onBack}>
            <ArrowLeft size={20} color="#162033" />
          </Pressable>
          <View style={styles.headerTitleBlock}>
            <Text style={styles.stockName}>{stockCode}</Text>
          </View>
        </View>
        <View style={styles.errorContainer}>
          <AlertTriangle size={48} color="#B42318" />
          <Text style={styles.errorText}>{error || t.home.dataLoadFailed}</Text>
          <Pressable style={styles.retryButton} onPress={handleRefresh}>
            <RefreshCcw size={16} color="#FFFFFF" />
            <Text style={styles.retryButtonText}>{t.home.retry}</Text>
          </Pressable>
        </View>
      </View>
    );
  }

  const { stock, factors, strategies, alerts, history } = detail;
  const isPositive = stock.change_percent >= 0;
  const scoreColor = getScoreColor(stock.score);

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
      <View style={styles.header}>
        <Pressable style={styles.backButton} onPress={onBack}>
          <ArrowLeft size={20} color="#162033" />
        </Pressable>
        <View style={styles.headerTitleBlock}>
          <Text style={styles.stockName}>{stock.name}</Text>
          <Text style={styles.stockCode}>{stock.code}</Text>
        </View>
        <Pressable style={styles.refreshButton} onPress={handleRefresh}>
          <RefreshCcw size={18} color="#0F8B8D" />
        </Pressable>
      </View>

      <ResearchPanel snapshot={researchSnapshot ?? null} />

      <View style={styles.pricePanel}>
        <View style={styles.priceBlock}>
          <Text style={styles.priceValue}>{formatPrice(stock.price)}</Text>
          <View style={[styles.changeBlock, { flexDirection: 'row', alignItems: 'center', gap: 6 }]}>
            {isPositive ? <TrendingUp size={16} color="#0F8B8D" /> : <TrendingDown size={16} color="#DC2626" />}
            <Text style={[styles.changeValue, { color: getChangeColor(stock.change_percent) }]}>
              {stock.change_percent >= 0 ? '+' : ''}{formatPercent(stock.change_percent)}
            </Text>
          </View>
        </View>
        <View style={[styles.scoreBlock, { borderColor: scoreColor }]}>
          <Text style={[styles.scoreValue, { color: scoreColor }]}>{stock.score}</Text>
          <Text style={styles.signalText}>{t.signal[stock.signal]}</Text>
        </View>
      </View>

      {history.length > 0 && <PriceChart stock={stock} history={history} />}

      <View style={styles.sectionHeader}>
        <Text style={styles.sectionTitle}>{t.factor.title}</Text>
      </View>
      <View style={styles.factorGrid}>
        {factors.map((factor) => (
          <FactorTile key={factor.key} factor={factor} />
        ))}
      </View>

      <View style={styles.sectionHeader}>
        <Text style={styles.sectionTitle}>{t.strategy.title}</Text>
      </View>
      {strategies.map((strategy) => (
        <StrategyCard
          key={strategy.id}
          detail={strategyDetails[`${stockCode}:${strategy.id}`]}
          isExpanded={expandedStrategyId === strategy.id}
          isLoading={loadingStrategyId === strategy.id}
          strategy={strategy}
          onPress={() => handleLoadStrategyDetail(strategy.id)}
        />
      ))}

      {dividendLoading ? (
        <ActivityIndicator size="small" color="#3B82F6" />
      ) : dividend.length > 0 ? (
        <>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>{t.detail.dividend}</Text>
          </View>
          <View style={styles.dividendContainer}>
            {dividend.map((record, index) => (
              <View key={index} style={styles.dividendCard}>
                <View style={styles.dividendHeader}>
                  <Text style={styles.dividendPlan}>{translateDividendPlan(record.div_proc, t)}</Text>
                </View>
                <View style={styles.dividendInfo}>
                  <View style={styles.dividendRow}>
                    <Text style={styles.dividendLabel}>{t.detail.announceDate}:</Text>
                    <Text style={styles.dividendValue}>{record.ann_date}</Text>
                  </View>
                  <View style={styles.dividendRow}>
                    <Text style={styles.dividendLabel}>{t.detail.recordDate}:</Text>
                    <Text style={styles.dividendValue}>{record.record_date}</Text>
                  </View>
                  <View style={styles.dividendRow}>
                    <Text style={styles.dividendLabel}>{t.detail.exDate}:</Text>
                    <Text style={styles.dividendValue}>{record.ex_date}</Text>
                  </View>
                  <View style={styles.dividendRow}>
                    <Text style={styles.dividendLabel}>{t.detail.payDate}:</Text>
                    <Text style={styles.dividendValue}>{record.pay_date}</Text>
                  </View>
                  <View style={styles.dividendRow}>
                    <Text style={styles.dividendLabel}>{t.detail.cashDividend}:</Text>
                    <Text style={styles.dividendValue}>{record.div_cash.toFixed(4)} {t.detail.currencyPerShare}</Text>
                  </View>
                  {(record.bonus_share > 0 || record.transfer_share > 0) && (
                    <>
                      <View style={styles.dividendRow}>
                        <Text style={styles.dividendLabel}>{t.detail.bonusShare}:</Text>
                        <Text style={styles.dividendValue}>{record.bonus_share}</Text>
                      </View>
                      <View style={styles.dividendRow}>
                        <Text style={styles.dividendLabel}>{t.detail.transferShare}:</Text>
                        <Text style={styles.dividendValue}>{record.transfer_share}</Text>
                      </View>
                    </>
                  )}
                </View>
              </View>
            ))}
          </View>
        </>
      ) : null}

      {newsLoading ? (
        <ActivityIndicator size="small" color="#3B82F6" />
      ) : news.length > 0 ? (
        <>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>{t.detail.news}</Text>
          </View>
          <View style={styles.newsContainer}>
            {news.map((item, index) => (
              <View key={index} style={styles.newsCard}>
                <Text style={styles.newsTitle}>{item.title}</Text>
                <Text style={styles.newsContent}>{item.content}</Text>
                <View style={styles.newsFooter}>
                  <Text style={styles.newsTime}>{item.pub_time}</Text>
                  <Text style={styles.newsSource}>{translateNewsSource(item.source, t)}</Text>
                </View>
              </View>
            ))}
          </View>
        </>
      ) : null}

      {instHoldLoading ? (
        <ActivityIndicator size="small" color="#3B82F6" />
      ) : instHold.length > 0 ? (
        <>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>{t.detail.institutionHoldings}</Text>
          </View>
          <View style={styles.instHoldContainer}>
            <View style={styles.instHoldHeaderRow}>
              <Text style={styles.instHoldHeader}>{t.detail.date}</Text>
              <Text style={styles.instHoldHeader}>{t.detail.instType}</Text>
              <Text style={styles.instHoldHeader}>{t.detail.holdAmount}</Text>
              <Text style={styles.instHoldHeader}>{t.detail.holdRatio}</Text>
              <Text style={styles.instHoldHeader}>{t.detail.changeAmount}</Text>
            </View>
            {instHold.map((record, index) => (
              <View key={index} style={styles.instHoldRow}>
                <Text style={styles.instHoldCell}>{record.trade_date}</Text>
                <Text style={styles.instHoldCell}>{translateInstType(record.inst_type, t)}</Text>
                <Text style={styles.instHoldCell}>{record.hold_amount.toFixed(0)}</Text>
                <Text style={styles.instHoldCell}>{record.hold_ratio.toFixed(2)}</Text>
                <Text style={[styles.instHoldCell, record.change_amount >= 0 ? styles.instHoldUp : styles.instHoldDown]}>
                  {record.change_amount >= 0 ? '+' : ''}{record.change_amount.toFixed(0)}
                </Text>
              </View>
            ))}
          </View>
        </>
      ) : null}

      <View style={styles.sectionHeader}>
        <Text style={styles.sectionTitle}>{t.home.riskAlertSection}</Text>
      </View>
      {alerts.length > 0 ? (
        alerts.map((alert) => (
          <AlertCard key={`${alert.level}-${alert.title}`} alert={alert} />
        ))
      ) : (
        <View style={styles.noAlertPanel}>
          <Text style={styles.noAlertText}>{t.home.noAlerts}</Text>
        </View>
      )}
    </ScrollView>
  );
}

function ResearchPanel({ snapshot }: { snapshot: ResearchSnapshot | null }) {
  const { t } = useTranslation();
  const marketScore = snapshot?.score ?? 0;
  const alertCount = snapshot?.alertCount ?? 0;
  const averageWinRate = snapshot?.averageWinRate ?? 0;

  return (
    <View style={styles.researchPanel}>
      <View style={styles.researchTopline}>
        <View style={styles.researchBadge}>
          <Sparkles size={14} color="#0F8B8D" />
          <Text style={styles.researchBadgeText}>{t.home.aiResearch}</Text>
        </View>
        <Text style={styles.researchRefreshText}>{snapshot?.dataStatus === 'mock' ? t.home.mockData : t.home.realtimeData}</Text>
      </View>
      <Text style={styles.researchTitle}>
        {snapshot?.stockName ? `${snapshot.stockName}: ${t.home.heroTitle}` : t.home.heroTitleDefault}
      </Text>
      <Text style={styles.researchCopy}>
        {snapshot?.aiSummary ?? t.home.aiSummaryLoading}
      </Text>
      <View style={styles.researchMetrics}>
        <View style={styles.researchMetric}>
          <Text style={styles.researchMetricLabel}>{t.home.metrics.overallScore}</Text>
          <Text style={styles.researchMetricValue}>{marketScore}<Text style={styles.researchMetricSuffix}>/100</Text></Text>
        </View>
        <View style={styles.researchMetric}>
          <Text style={styles.researchMetricLabel}>{t.home.metrics.riskAlert}</Text>
          <Text style={styles.researchMetricValue}>{alertCount}<Text style={styles.researchMetricSuffix}> item</Text></Text>
        </View>
        <View style={styles.researchMetric}>
          <Text style={styles.researchMetricLabel}>{t.home.metrics.winRate}</Text>
          <Text style={styles.researchMetricValue}>{averageWinRate}<Text style={styles.researchMetricSuffix}>%</Text></Text>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F6F7FB' },
  screenContainer: { flex: 1, backgroundColor: '#F6F7FB', paddingHorizontal: 20, paddingTop: 20 },
  content: { padding: 20, paddingBottom: 36, gap: 18 },
  header: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: 12,
    marginBottom: 8,
  },
  backButton: {
    alignItems: 'center',
    backgroundColor: '#FFFFFF',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#E5E7EB',
    height: 40,
    justifyContent: 'center',
    width: 40,
  },
  headerTitleBlock: { flex: 1, gap: 4 },
  stockName: { color: '#162033', fontSize: 20, fontWeight: '800' },
  stockCode: { color: '#6B7280', fontSize: 13 },
  refreshButton: {
    alignItems: 'center',
    backgroundColor: '#E9FBF7',
    borderRadius: 8,
    height: 40,
    justifyContent: 'center',
    width: 40,
  },
  researchPanel: {
    backgroundColor: '#162033',
    borderRadius: 12,
    gap: 16,
    padding: 18,
  },
  researchTopline: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  researchBadge: {
    alignItems: 'center',
    backgroundColor: '#E9FBF7',
    borderRadius: 8,
    flexDirection: 'row',
    gap: 6,
    paddingHorizontal: 10,
    paddingVertical: 6,
  },
  researchBadgeText: {
    color: '#0F766E',
    fontSize: 12,
    fontWeight: '700',
  },
  researchRefreshText: {
    color: '#C7D2FE',
    fontSize: 12,
  },
  researchTitle: {
    color: '#FFFFFF',
    fontSize: 25,
    fontWeight: '800',
    lineHeight: 34,
  },
  researchCopy: {
    color: '#D1D5DB',
    fontSize: 14,
    lineHeight: 22,
  },
  researchMetrics: {
    flexDirection: 'row',
    gap: 10,
  },
  researchMetric: {
    flex: 1,
    gap: 5,
    minWidth: 0,
  },
  researchMetricLabel: {
    color: '#C7D2FE',
    fontSize: 12,
  },
  researchMetricValue: {
    color: '#FFFFFF',
    fontSize: 22,
    fontWeight: '800',
  },
  researchMetricSuffix: {
    color: '#D1D5DB',
    fontSize: 13,
    fontWeight: '600',
  },
  pricePanel: {
    alignItems: 'center',
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    flexDirection: 'row',
    gap: 20,
    padding: 20,
    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.08)',
  },
  priceBlock: { flex: 1, gap: 8 },
  priceValue: { color: '#162033', fontSize: 32, fontWeight: '800' },
  changeBlock: { alignItems: 'center', flexDirection: 'row', gap: 6 },
  changeValue: { fontSize: 16, fontWeight: '700' },
  scoreBlock: {
    alignItems: 'center',
    borderRadius: 12,
    borderWidth: 2,
    gap: 4,
    paddingHorizontal: 16,
    paddingVertical: 12,
  },
  scoreValue: { fontSize: 28, fontWeight: '800' },
  signalText: { color: '#6B7280', fontSize: 12 },
  sectionHeader: { marginTop: 8 },
  sectionTitle: { color: '#162033', fontSize: 18, fontWeight: '800' },
  factorGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  noAlertPanel: {
    alignItems: 'center',
    backgroundColor: '#ECFDF3',
    borderRadius: 8,
    padding: 16,
  },
  noAlertText: { color: '#065F46', fontSize: 14 },
  loadingContainer: {
    alignItems: 'center',
    flex: 1,
    justifyContent: 'center',
    gap: 12,
  },
  loadingText: { color: '#6B7280', fontSize: 14 },
  loadingTitle: { color: '#6B7280', fontSize: 20, fontWeight: '800' },
  errorContainer: {
    alignItems: 'center',
    flex: 1,
    justifyContent: 'center',
    gap: 16,
    padding: 20,
  },
  errorText: { color: '#B42318', fontSize: 16, textAlign: 'center' },
  retryButton: {
    alignItems: 'center',
    backgroundColor: '#0F8B8D',
    borderRadius: 8,
    flexDirection: 'row',
    gap: 8,
    paddingHorizontal: 20,
    paddingVertical: 12,
  },
  retryButtonText: { color: '#FFFFFF', fontSize: 14, fontWeight: '700' },
  instHoldContainer: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    overflow: 'hidden',
    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.08)',
  },
  instHoldHeaderRow: {
    flexDirection: 'row',
    padding: 12,
    backgroundColor: '#F9FAFB',
    borderBottomWidth: 1,
    borderBottomColor: '#E5E7EB',
  },
  instHoldHeader: {
    flex: 1,
    color: '#6B7280',
    fontSize: 12,
    fontWeight: '600',
    textAlign: 'center',
  },
  instHoldRow: {
    flexDirection: 'row',
    padding: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#F3F4F6',
  },
  instHoldCell: {
    flex: 1,
    color: '#1F2937',
    fontSize: 12,
    textAlign: 'center',
  },
  instHoldUp: {
    color: '#0F8B8D',
    fontWeight: '600',
  },
  instHoldDown: {
    color: '#DC2626',
    fontWeight: '600',
  },
  dividendContainer: {
    gap: 12,
  },
  dividendCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    overflow: 'hidden',
    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.08)',
  },
  dividendHeader: {
    backgroundColor: '#FEF3C7',
    padding: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#FDE68A',
  },
  dividendPlan: {
    color: '#92400E',
    fontSize: 14,
    fontWeight: '600',
  },
  dividendInfo: {
    padding: 12,
    gap: 8,
  },
  dividendRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  dividendLabel: {
    color: '#6B7280',
    fontSize: 13,
  },
  dividendValue: {
    color: '#1F2937',
    fontSize: 13,
    fontWeight: '500',
  },
  newsContainer: {
    gap: 12,
  },
  newsCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 16,
    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.08)',
  },
  newsTitle: {
    color: '#162033',
    fontSize: 15,
    fontWeight: '700',
    marginBottom: 8,
  },
  newsContent: {
    color: '#4B5563',
    fontSize: 13,
    lineHeight: 1.6,
    marginBottom: 12,
  },
  newsFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  newsTime: {
    color: '#9CA3AF',
    fontSize: 12,
  },
  newsSource: {
    color: '#3B82F6',
    fontSize: 12,
  },
  offlineContainer: {
    alignItems: 'center',
    flex: 1,
    justifyContent: 'center',
    gap: 16,
    padding: 20,
  },
  offlineTitle: { color: '#92400E', fontSize: 18, fontWeight: '700' },
  offlineText: { color: '#B45309', fontSize: 14, textAlign: 'center', lineHeight: 1.6 },
  offlineRetryButton: {
    alignItems: 'center',
    backgroundColor: '#F59E0B',
    borderRadius: 8,
    flexDirection: 'row',
    gap: 8,
    paddingHorizontal: 20,
    paddingVertical: 12,
  },
  offlineRetryButtonText: { color: '#FFFFFF', fontSize: 14, fontWeight: '700' },
});
