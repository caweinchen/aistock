import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { AlertTriangle, Bell, ChevronRight, Globe, LogOut, RefreshCcw, Search, Settings, Sparkles, User, X } from 'lucide-react-native';
import { StockRow } from '../components/StockRow';
import { FactorTile } from '../components/FactorTile';
import { StrategyCard } from '../components/StrategyCard';
import { AlertCard } from '../components/AlertCard';
import { PriceChart } from '../components/PriceChart';
import { BacktestBuilder } from '../components/BacktestBuilder';
import { useStockData } from '../hooks/useStockData';
import { formatPrice, formatUpdatedAt, getChangeColor } from '../utils/formatters';
import type { StrategyTemplate } from '../types';
import { useState } from 'react';
import { useTranslation, type Locale } from '../i18n';

interface HomeScreenProps {
  onOpenSettings?: () => void;
  onOpenProfile?: () => void;
  onLogout?: () => void;
}

export function HomeScreen({ onOpenSettings, onOpenProfile, onLogout }: HomeScreenProps) {
  const { t, locale, setLocale } = useTranslation();
  const {
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
  } = useStockData();

  const [isSearchVisible, setIsSearchVisible] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [updatingWatchlistCode, setUpdatingWatchlistCode] = useState<string | null>(null);
  const [expandedStrategyId, setExpandedStrategyId] = useState<string | null>(null);
  const [loadingStrategyId, setLoadingStrategyId] = useState<string | null>(null);
  const [strategyDetails, setStrategyDetails] = useState<Record<string, unknown>>({});
  const [isBuilderOpen, setIsBuilderOpen] = useState(false);
  const [backtestName, setBacktestName] = useState(t.home.myStrategy);
  const [backtestTemplate, setBacktestTemplate] = useState<StrategyTemplate>('trend-breakout');
  const [lookbackDays, setLookbackDays] = useState(180);
  const [isCreatingBacktest, setIsCreatingBacktest] = useState(false);
  const localeLabel = locale === 'zh' ? '中' : locale === 'zh-Hant' ? '繁' : 'EN';

  const selectedStock = detail?.stock ?? stocks.find((stock) => stock.code === selectedCode) ?? stocks[0];
  const marketScore = selectedStock?.score ?? 0;
  const alertCount = detail?.alerts.length ?? 0;
  
  const averageWinRate = detail?.strategies.length
    ? Math.round(detail.strategies.reduce((sum, s) => sum + s.win_rate, 0) / detail.strategies.length)
    : 0;

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
    await toggleWatchlist(stock);
    setUpdatingWatchlistCode(null);
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
      <View style={styles.header}>
        <View style={styles.headerTitleBlock}>
          <Text style={styles.appName}>AIStock</Text>
          <Text style={styles.subtleText}>{t.home.subtitle}</Text>
        </View>
        <View style={styles.headerActions}>
          <Pressable onPress={() => setIsSearchVisible((v) => !v)}>
            <Search size={20} color="#162033" />
          </Pressable>
          <Pressable>
            <Bell size={20} color="#162033" />
          </Pressable>
          <Pressable onPress={onOpenSettings}>
            <Settings size={20} color="#162033" />
          </Pressable>
          {onOpenProfile && (
            <Pressable onPress={onOpenProfile}>
              <User size={20} color="#162033" />
            </Pressable>
          )}
          {onLogout && (
            <Pressable onPress={onLogout}>
              <LogOut size={20} color="#162033" />
            </Pressable>
          )}
          <Pressable
            accessibilityLabel={t.common.switchLanguage}
            accessibilityRole="button"
            style={styles.langButton}
            onPress={() => {
              const locales: Locale[] = ['zh', 'zh-Hant', 'en'];
              const currentIndex = locales.indexOf(locale);
              const nextLocale = locales[(currentIndex + 1) % locales.length];
              setLocale(nextLocale);
            }}
          >
            <Globe size={15} color="#FFFFFF" />
            <Text style={styles.langButtonText}>{localeLabel}</Text>
          </Pressable>
        </View>
      </View>

      {isSearchVisible && (
        <View style={styles.searchPanel}>
          <Search size={18} color="#6B7280" />
          <TextInput
            style={styles.searchInput}
            value={searchQuery}
            onChangeText={setSearchQuery}
            onSubmitEditing={() => void loadStocks(searchQuery)}
            placeholder={t.stock.search}
            placeholderTextColor="#9CA3AF"
          />
          {searchQuery && (
            <Pressable onPress={() => { setSearchQuery(''); void loadStocks(); }}>
              <X size={16} color="#6B7280" />
            </Pressable>
          )}
          <Pressable style={styles.searchButton} onPress={() => void loadStocks(searchQuery)}>
            <Text style={styles.searchButtonText}>{t.common.ok}</Text>
          </Pressable>
        </View>
      )}

      {error && (
        <View style={styles.errorPanel}>
          <AlertTriangle size={20} color="#B42318" />
          <View style={styles.errorCopy}>
            <Text style={styles.errorTitle}>{t.home.dataLoadFailed}</Text>
            <Text style={styles.errorText}>{error}</Text>
            <Pressable style={styles.retryButton} onPress={() => void loadStocks(searchQuery)}>
              <RefreshCcw size={16} color="#FFFFFF" />
              <Text style={styles.retryButtonText}>{t.home.retry}</Text>
            </Pressable>
          </View>
        </View>
      )}

      <View style={styles.heroPanel}>
        <View style={styles.heroTopline}>
          <View style={styles.badge}>
            <Sparkles size={14} color="#0F8B8D" />
            <Text style={styles.badgeText}>{t.home.aiResearch}</Text>
          </View>
          <Text style={styles.refreshText}>{detail?.data_status === 'mock' ? t.home.mockData : t.home.realtimeData}</Text>
        </View>
        <Text style={styles.heroTitle}>
          {selectedStock ? `${selectedStock.name}：${t.home.heroTitle}` : t.home.heroTitleDefault}
        </Text>
        <Text style={styles.heroCopy}>
          {detail?.ai_summary ?? t.home.aiSummaryLoading}
        </Text>
        <View style={styles.heroMetrics}>
          <Metric label={t.home.metrics.overallScore} value={String(marketScore)} suffix="/100" inverted />
          <Metric label={t.home.metrics.riskAlert} value={String(alertCount)} suffix=" 条" inverted />
          <Metric label={t.home.metrics.winRate} value={String(averageWinRate)} suffix="%" inverted />
        </View>
      </View>

      <View style={styles.sectionHeader}>
        <Text style={styles.sectionTitle}>{t.stock.watchlist}</Text>
        <Pressable style={styles.textButton} onPress={() => void loadStocks(searchQuery)}>
          {isLoadingStocks && <ActivityIndicator size="small" color="#0F8B8D" />}
          <Text style={styles.textButtonLabel}>{t.common.ok}</Text>
          <RefreshCcw size={15} color="#0F8B8D" />
        </Pressable>
      </View>

      <View style={styles.stockList}>
        {stocks.map((stock) => (
          <StockRow
            key={stock.code}
            isInWatchlist={watchlistCodes.has(stock.code)}
            isSelected={stock.code === selectedCode}
            isUpdatingWatchlist={updatingWatchlistCode === stock.code}
            stock={stock}
            onPress={() => void loadStockDetail(stock.code)}
            onToggleWatchlist={() => handleToggleWatchlist(stock)}
          />
        ))}
        {!stocks.length && !isLoadingStocks && <Text style={styles.emptyText}>{t.home.noStocks}</Text>}
      </View>

      {selectedStock && (
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

      {detail?.history?.length && <PriceChart stock={selectedStock} history={detail.history} />}

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
    </ScrollView>
  );
}

function Metric({ label, value, suffix, inverted = false }: { label: string; value: string; suffix: string; inverted?: boolean }) {
  return (
    <View style={styles.metric}>
      <Text style={[styles.metricLabel, inverted && styles.metricLabelInverted]}>{label}</Text>
      <Text style={[styles.metricValue, inverted && styles.metricValueInverted]}>
        {value}<Text style={[styles.metricSuffix, inverted && styles.metricSuffixInverted]}>{suffix}</Text>
      </Text>
    </View>
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
  header: { alignItems: 'center', flexDirection: 'row', gap: 12, justifyContent: 'space-between' },
  headerTitleBlock: { flex: 1, minWidth: 0 },
  appName: { color: '#162033', fontSize: 26, fontWeight: '800' },
  subtleText: { color: '#6B7280', fontSize: 13 },
  headerActions: { alignItems: 'center', flexDirection: 'row', flexShrink: 0, gap: 12 },
  langButton: {
    alignItems: 'center',
    backgroundColor: '#0F8B8D',
    borderRadius: 8,
    flexDirection: 'row',
    gap: 5,
    height: 36,
    justifyContent: 'center',
    paddingHorizontal: 10,
    minWidth: 58,
  },
  langButtonText: {
    color: '#FFFFFF',
    fontSize: 13,
    fontWeight: '800',
  },
  searchPanel: {
    alignItems: 'center',
    backgroundColor: '#FFFFFF',
    borderColor: '#D8DEE9',
    borderRadius: 8,
    borderWidth: 1,
    flexDirection: 'row',
    gap: 8,
    minHeight: 48,
    paddingHorizontal: 12,
  },
  searchInput: { color: '#162033', flex: 1, fontSize: 15, minWidth: 0, paddingVertical: 8 },
  searchButton: {
    alignItems: 'center',
    backgroundColor: '#0F8B8D',
    borderRadius: 8,
    height: 34,
    justifyContent: 'center',
    paddingHorizontal: 12,
  },
  searchButtonText: { color: '#FFFFFF', fontSize: 13, fontWeight: '800' },
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
  heroPanel: { backgroundColor: '#162033', borderRadius: 8, gap: 16, padding: 18 },
  heroTopline: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between' },
  badge: {
    alignItems: 'center',
    backgroundColor: '#E9FBF7',
    borderRadius: 8,
    flexDirection: 'row',
    gap: 6,
    paddingHorizontal: 10,
    paddingVertical: 6,
  },
  badgeText: { color: '#0F766E', fontSize: 12, fontWeight: '700' },
  refreshText: { color: '#C7D2FE', fontSize: 12 },
  heroTitle: { color: '#FFFFFF', fontSize: 25, fontWeight: '800', lineHeight: 34 },
  heroCopy: { color: '#D1D5DB', fontSize: 14, lineHeight: 22 },
  heroMetrics: { flexDirection: 'row', gap: 10 },
  metric: { flex: 1, gap: 5, minWidth: 0 },
  metricLabel: { color: '#6B7280', fontSize: 12 },
  metricLabelInverted: { color: '#C7D2FE' },
  metricValue: { color: '#162033', fontSize: 22, fontWeight: '800' },
  metricValueInverted: { color: '#FFFFFF' },
  metricSuffix: { color: '#6B7280', fontSize: 13, fontWeight: '600' },
  metricSuffixInverted: { color: '#D1D5DB' },
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
});
