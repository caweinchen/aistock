import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';
import { ChevronDown, ChevronUp, LineChart, ShieldCheck } from 'lucide-react-native';
import type { StrategyDetail, StrategyResult } from '../types';
import { formatPercent, getRiskColor } from '../utils/formatters';
import { useTranslateRisk, useTranslateAction, useTranslation } from '../i18n';

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

  return (
    <Pressable style={({ pressed }) => [styles.strategyCard, pressed && styles.strategyCardPressed]} onPress={onPress}>
      <View style={styles.strategyHeader}>
        <View style={styles.strategyTitleLine}>
          <LineChart size={20} color="#162033" />
          <Text style={styles.strategyName}>{strategy.name}</Text>
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

  return (
    <View style={styles.strategyDetailPanel}>
      <View style={styles.strategyDetailStats}>
        <Metric label={t.strategy.annualizedReturn} value={formatPercent(detail.annualized_return)} suffix="" />
        <Metric label={t.strategy.sharpeRatio} value={detail.sharpe_ratio.toFixed(2)} suffix="" />
        <Metric label={t.strategy.tradeCount} value={String(detail.trade_count)} suffix="" />
      </View>
      <View style={styles.ruleList}>
        {detail.rules.map((rule) => (
          <View key={rule} style={styles.ruleItem}>
            <View style={styles.ruleDot} />
            <Text style={styles.ruleText}>{rule}</Text>
          </View>
        ))}
      </View>
      <View style={styles.tradeList}>
        {detail.trades.map((trade) => {
          const translatedAction = useTranslateAction(trade.action);
          return (
            <View key={`${trade.date}-${trade.action}-${trade.price}`} style={styles.tradeRow}>
              <View>
                <Text style={styles.tradeDate}>{trade.date}</Text>
                <Text style={styles.tradeReason}>{trade.reason}</Text>
              </View>
              <View style={styles.tradeActionBlock}>
                <Text style={[styles.tradeAction, { color: trade.action === 'buy' ? '#0F8B8D' : '#DC2626' }]}>
                  {translatedAction}
                </Text>
                <Text style={styles.tradePrice}>{trade.price.toFixed(2)}</Text>
              </View>
            </View>
          );
        })}
      </View>
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