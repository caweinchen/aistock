import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';
import { ChevronDown, ChevronUp, LineChart, ShieldCheck } from 'lucide-react-native';
import type { StrategyDetail, StrategyResult } from '../types';
import { formatPercent, getRiskColor } from '../utils/formatters';
import { useTranslateRisk, useTranslateStrategyName, useTranslation } from '../i18n';

interface StrategyCardProps {
  strategy: StrategyResult;
  detail?: StrategyDetail;
  isExpanded: boolean;
  isLoading: boolean;
  onPress: () => void;
}

export function StrategyCard({ strategy, detail, isExpanded, isLoading, onPress }: StrategyCardProps) {
  const { t } = useTranslation();
  const riskColor = getRiskColor(strategy.risk);
  const progressWidth = `${Math.max(8, Math.min(100, strategy.win_rate))}%` as const;
  const translatedRisk = useTranslateRisk(strategy.risk);
  const translatedName = useTranslateStrategyName(strategy.name);

  return (
    <Pressable style={({ pressed }) => [styles.strategyCard, pressed && styles.strategyCardPressed]} onPress={onPress}>
      <View style={styles.strategyHeader}>
        <View style={styles.strategyTitleLine}>
          <LineChart size={20} color="#162033" />
          <Text style={styles.strategyName}>{translatedName}</Text>
        </View>
        <View style={[styles.riskBadge, { backgroundColor: `${riskColor}1A` }]}>
          <ShieldCheck size={14} color={riskColor} />
          <Text style={[styles.riskLabel, { color: riskColor }]}>{translatedRisk} {t.strategy.risk}</Text>
        </View>
      </View>
      <View style={styles.strategyStats}>
        <Metric label={strategy.period} value={formatPercent(strategy.return_rate)} suffix="" />
        <Metric label={t.strategy.maxDrawdown} value={formatPercent(strategy.max_drawdown)} suffix="" />
        <Metric label={t.strategy.winRate} value={String(Math.round(strategy.win_rate))} suffix="%" />
      </View>
      <Text style={styles.strategySummary}>{strategy.summary}</Text>
      <View style={styles.progressTrack}>
        <View style={[styles.progressFill, { width: progressWidth }]} />
      </View>
      <View style={styles.strategyExpandLine}>
        {isLoading ? <ActivityIndicator size="small" color="#0F8B8D" /> : null}
        <Text style={styles.strategyExpandText}>{isExpanded ? t.strategy.collapseDetail : t.strategy.viewDetail}</Text>
        {isExpanded ? <ChevronUp size={16} color="#0F8B8D" /> : <ChevronDown size={16} color="#0F8B8D" />}
      </View>
      {isExpanded ? <StrategyDetailPanel detail={detail!} /> : null}
    </Pressable>
  );
}

function Metric({ label, value, suffix }: { label: string; value: string; suffix: string }) {
  return (
    <View style={styles.metric}>
      <Text style={styles.metricLabel}>{label}</Text>
      <Text style={styles.metricValue}>
        {value}
        <Text style={styles.metricSuffix}>{suffix}</Text>
      </Text>
    </View>
  );
}

function StrategyDetailPanel({ detail }: { detail?: StrategyDetail }) {
  const { t } = useTranslation();

  if (!detail) {
    return (
      <View style={styles.strategyDetailPanel}>
        <Text style={styles.loadingText}>{t.common.loading}</Text>
      </View>
    );
  }

  const ruleMap: Record<string, keyof typeof t.strategy> = {
    'Buy when close crosses above the 20-day moving average.': 'ruleTrendBreakout1',
    'Sell when close falls below the 20-day moving average or stop-loss is triggered.': 'ruleTrendBreakout2',
    'Volume expansion strengthens the breakout reason when available.': 'ruleTrendBreakout3',
    'Buy when price recovers from the recent low range.': 'ruleLowValuation1',
    'Sell when price reverts toward the recent high range or stop-loss is triggered.': 'ruleLowValuation2',
    'Use recent price range as a valuation proxy until valuation data is available.': 'ruleLowValuation3',
    'Buy only when trend is stable and realized volatility is moderate.': 'ruleDividend1',
    'Sell when trend weakens, volatility rises, or stop-loss is triggered.': 'ruleDividend2',
    'Use defensive price behavior as a dividend proxy until dividend data is available.': 'ruleDividend3',
  };

  const reasonMap: Record<string, keyof typeof t.strategy> = {
    'Close crossed above the 20-day moving average.': 'reasonCrossAbove',
    'Close fell below the 20-day moving average or stop-loss was hit.': 'reasonCrossBelow',
    'Price recovered from the recent low range.': 'reasonRecoverLow',
    'Price reverted toward the recent high range or stop-loss was hit.': 'reasonRevertHigh',
    'Trend was stable with moderate realized volatility.': 'reasonStableTrend',
    'Trend weakened, volatility rose, or stop-loss was hit.': 'reasonTrendWeak',
    'Closing position at backtest end.': 'reasonClosePosition',
  };

  const translateRule = (rule: string) => {
    const key = ruleMap[rule];
    return key ? t.strategy[key] : rule;
  };

  const translateAction = (action: string) => {
    return t.action[action as keyof typeof t.action] || action;
  };

  const translateReason = (reason: string) => {
    const key = reasonMap[reason];
    return key ? t.strategy[key] : reason;
  };

  const rules = detail.rules || [];
  const trades = detail.trades || [];

  return (
    <View style={styles.strategyDetailPanel}>
      <View style={styles.strategyDetailStats}>
        <Metric label={t.strategy.annualizedReturn} value={formatPercent(detail.annualized_return || 0)} suffix="" />
        <Metric label={t.strategy.sharpeRatio} value={(detail.sharpe_ratio || 0).toFixed(2)} suffix="" />
        <Metric label={t.strategy.tradeCount} value={String(detail.trade_count || 0)} suffix="" />
      </View>
      {rules.length > 0 && (
        <View style={styles.ruleList}>
          {rules.map((rule, index) => {
            const translatedRule = translateRule(rule);
            return (
              <View key={index} style={styles.ruleItem}>
                <View style={styles.ruleDot} />
                <Text style={styles.ruleText}>{translatedRule}</Text>
              </View>
            );
          })}
        </View>
      )}
      {trades.length > 0 && (
        <View style={styles.tradeList}>
          {trades.map((trade) => {
            const translatedAction = translateAction(trade.action);
            const translatedReason = translateReason(trade.reason);
            return (
              <View key={`${trade.date}-${trade.action}-${trade.price}`} style={styles.tradeRow}>
                <View>
                  <Text style={styles.tradeDate}>{trade.date}</Text>
                  <Text style={styles.tradeReason}>{translatedReason}</Text>
                </View>
                <View style={styles.tradeActionBlock}>
                  <Text style={[styles.tradeAction, { color: trade.action === 'buy' ? '#0F8B8D' : '#DC2626' }]}>
                    {translatedAction}
                  </Text>
                  <Text style={styles.tradePrice}>{(trade.price || 0).toFixed(2)}</Text>
                </View>
              </View>
            );
          })}
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  strategyCard: {
    backgroundColor: '#FFFFFF',
    borderColor: '#E5E7EB',
    borderRadius: 8,
    borderWidth: 1,
    gap: 16,
    padding: 16,
  },
  strategyCardPressed: {
    opacity: 0.86,
  },
  strategyHeader: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: 12,
  },
  strategyTitleLine: {
    alignItems: 'center',
    flexDirection: 'row',
    flexShrink: 1,
    gap: 8,
  },
  strategyName: {
    color: '#162033',
    fontSize: 17,
    fontWeight: '800',
  },
  riskBadge: {
    alignItems: 'center',
    borderRadius: 8,
    flexDirection: 'row',
    gap: 4,
    paddingHorizontal: 8,
    paddingVertical: 5,
  },
  riskLabel: {
    fontSize: 12,
    fontWeight: '800',
  },
  strategyStats: {
    flexDirection: 'row',
    gap: 16,
  },
  metric: {
    flex: 1,
    gap: 5,
    minWidth: 0,
  },
  metricLabel: {
    color: '#6B7280',
    fontSize: 12,
  },
  metricValue: {
    color: '#162033',
    fontSize: 22,
    fontWeight: '800',
  },
  metricSuffix: {
    color: '#6B7280',
    fontSize: 13,
    fontWeight: '600',
  },
  strategySummary: {
    color: '#4B5563',
    fontSize: 13,
    lineHeight: 20,
  },
  progressTrack: {
    backgroundColor: '#EEF2F7',
    borderRadius: 999,
    height: 8,
    overflow: 'hidden',
  },
  progressFill: {
    backgroundColor: '#0F8B8D',
    height: '100%',
  },
  strategyExpandLine: {
    alignItems: 'center',
    borderTopColor: '#EEF2F7',
    borderTopWidth: 1,
    flexDirection: 'row',
    gap: 6,
    justifyContent: 'center',
    minHeight: 34,
    paddingTop: 8,
  },
  strategyExpandText: {
    color: '#0F8B8D',
    fontSize: 13,
    fontWeight: '800',
  },
  loadingText: {
    color: '#6B7280',
    fontSize: 14,
    textAlign: 'center',
  },
  strategyDetailPanel: {
    backgroundColor: '#F8FAFC',
    borderColor: '#E5E7EB',
    borderRadius: 8,
    borderWidth: 1,
    gap: 14,
    padding: 12,
  },
  strategyDetailStats: {
    flexDirection: 'row',
    gap: 12,
  },
  ruleList: {
    gap: 8,
  },
  ruleItem: {
    flexDirection: 'row',
    gap: 8,
  },
  ruleDot: {
    backgroundColor: '#0F8B8D',
    borderRadius: 999,
    height: 6,
    marginTop: 7,
    width: 6,
  },
  ruleText: {
    color: '#4B5563',
    flex: 1,
    fontSize: 13,
    lineHeight: 20,
  },
  tradeList: {
    backgroundColor: '#FFFFFF',
    borderColor: '#E5E7EB',
    borderRadius: 8,
    borderWidth: 1,
    overflow: 'hidden',
  },
  tradeRow: {
    alignItems: 'center',
    borderBottomColor: '#EEF2F7',
    borderBottomWidth: 1,
    flexDirection: 'row',
    gap: 10,
    justifyContent: 'space-between',
    minHeight: 72,
    padding: 10,
  },
  tradeDate: {
    color: '#162033',
    fontSize: 13,
    fontWeight: '800',
  },
  tradeReason: {
    color: '#6B7280',
    flexShrink: 1,
    fontSize: 12,
    lineHeight: 18,
    maxWidth: 190,
  },
  tradeActionBlock: {
    alignItems: 'flex-end',
    gap: 3,
  },
  tradeAction: {
    fontSize: 13,
    fontWeight: '800',
  },
  tradePrice: {
    color: '#162033',
    fontSize: 13,
    fontWeight: '700',
  },
});