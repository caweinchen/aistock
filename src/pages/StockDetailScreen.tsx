import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { ArrowLeft, AlertTriangle, TrendingUp, TrendingDown, RefreshCcw } from 'lucide-react-native';
import { FactorTile } from '../components/FactorTile';
import { StrategyCard } from '../components/StrategyCard';
import { AlertCard } from '../components/AlertCard';
import { PriceChart } from '../components/PriceChart';
import type { StockDetail, StrategyDetail, InstHoldRecord, DividendRecord, StockNews } from '../types';
import { useTranslation } from '../i18n';
import { formatPrice, formatPercent, formatUpdatedAt, getChangeColor, getScoreColor } from '../utils/formatters';
import { useState, useEffect } from 'react';
import { getStockDetail, getStrategyDetail, getStockInstHold, getStockDividend, getStockNews } from '../services/api';

interface StockDetailScreenProps {
  stockCode: string;
  onBack: () => void;
}

export function StockDetailScreen({ stockCode, onBack }: StockDetailScreenProps) {
  const { t, locale } = useTranslation();
  const [detail, setDetail] = useState<StockDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedStrategyId, setExpandedStrategyId] = useState<string | null>(null);
  const [loadingStrategyId, setLoadingStrategyId] = useState<string | null>(null);
  const [strategyDetails, setStrategyDetails] = useState<Record<string, StrategyDetail>>({});
  const [instHold, setInstHold] = useState<InstHoldRecord[]>([]);
  const [instHoldLoading, setInstHoldLoading] = useState(false);
  const [dividend, setDividend] = useState<DividendRecord[]>([]);
  const [dividendLoading, setDividendLoading] = useState(false);
  const [news, setNews] = useState<StockNews[]>([]);
  const [newsLoading, setNewsLoading] = useState(false);

  useEffect(() => {
    void loadDetail(true);
    void loadInstHold();
    void loadDividend();
    void loadNews();
  }, [stockCode]);

  const loadInstHold = async () => {
    if (!stockCode) return;
    setInstHoldLoading(true);
    try {
      const data = await getStockInstHold(stockCode);
      setInstHold(data);
    } catch (err) {
      console.warn('Failed to load institution holdings:', err);
    } finally {
      setInstHoldLoading(false);
    }
  };

  const loadDividend = async () => {
    if (!stockCode) return;
    setDividendLoading(true);
    try {
      const data = await getStockDividend(stockCode);
      setDividend(data);
    } catch (err) {
      console.warn('Failed to load dividend records:', err);
    } finally {
      setDividendLoading(false);
    }
  };

  const loadNews = async () => {
    if (!stockCode) return;
    setNewsLoading(true);
    try {
      const data = await getStockNews(stockCode);
      setNews(data);
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
    try {
      const data = await getStockDetail(stockCode, forceRefresh);
      setDetail(data);
    } catch (err) {
      setError(t.error.fetchStockDetail);
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
      const result = await getStrategyDetail(stockCode, strategyId);
      const key = `${stockCode}:${strategyId}`;
      setStrategyDetails((current) => ({ ...current, [key]: result }));
    } catch (err) {
      setError(t.error.fetchStrategy);
    } finally {
      setLoadingStrategyId(null);
    }
  };

  const handleRefresh = async () => {
    await loadDetail(true);
  };

  if (isLoading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#0F8B8D" />
        <Text style={styles.loadingText}>{t.home.loadingDetail}</Text>
      </View>
    );
  }

  if (error || !detail) {
    return (
      <View style={styles.errorContainer}>
        <AlertTriangle size={48} color="#B42318" />
        <Text style={styles.errorText}>{error || t.home.dataLoadFailed}</Text>
        <Pressable style={styles.retryButton} onPress={handleRefresh}>
          <RefreshCcw size={16} color="#FFFFFF" />
          <Text style={styles.retryButtonText}>{t.home.retry}</Text>
        </Pressable>
      </View>
    );
  }

  const { stock, factors, strategies, alerts, history, ai_summary, updated_at } = detail;
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

      <View style={styles.heroPanel}>
        <Text style={styles.heroTitle}>{t.home.aiResearch}</Text>
        <Text style={styles.heroSummary}>
          {ai_summary ?? t.home.aiSummaryDefault}
        </Text>
        {updated_at && (
          <Text style={styles.updateTime}>
            {formatUpdatedAt(updated_at, locale === 'zh' ? 'zh-CN' : locale === 'zh-Hant' ? 'zh-TW' : 'en-US', t.formatter.updated)}
          </Text>
        )}
      </View>

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
                  <Text style={styles.dividendPlan}>{record.div_proc}</Text>
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
                    <Text style={styles.dividendValue}>¥{record.div_cash.toFixed(4)}</Text>
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
                  <Text style={styles.newsSource}>{item.source}</Text>
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
                <Text style={styles.instHoldCell}>{record.inst_type}</Text>
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

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F6F7FB' },
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
  heroPanel: {
    backgroundColor: '#162033',
    borderRadius: 12,
    gap: 12,
    padding: 18,
  },
  heroTitle: {
    color: '#0F8B8D',
    fontSize: 13,
    fontWeight: '700',
    letterSpacing: 0.5,
    textTransform: 'uppercase',
  },
  heroSummary: { color: '#D1D5DB', fontSize: 14, lineHeight: 22 },
  updateTime: { color: '#6B7280', fontSize: 12 },
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
});