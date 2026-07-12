import { useMemo, useState } from 'react';
import { ActivityIndicator, Pressable, StyleSheet, Text, View } from 'react-native';
import { AlertTriangle, ChevronRight, RefreshCcw } from 'lucide-react-native';
import type { WatchlistFocusLevel, WatchlistInsights, WatchlistSortMode } from '../types';
import { groupInsights, sortInsights } from '../services/watchlistInsights';

const groups: WatchlistFocusLevel[] = ['priority', 'watch', 'cautious', 'insufficient_data'];
interface Props {
  insights: WatchlistInsights | null;
  loading: boolean;
  error: boolean;
  locale: string;
  onRetry: () => void;
  onOpenStock: (code: string) => void;
}

export function WatchlistInsightsPanel({ insights, loading, error, locale, onRetry, onOpenStock }: Props) {
  const [sortMode, setSortMode] = useState<WatchlistSortMode>('overall');
  const [activeGroup, setActiveGroup] = useState<WatchlistFocusLevel>('priority');
  const intelligenceItems = insights?.intelligence?.insights ?? [];
  const grouped = useMemo(() => groupInsights(sortInsights(intelligenceItems, sortMode)), [intelligenceItems, sortMode]);
  const labels = locale === 'en'
    ? { title: 'Watchlist insights', risk: 'Overall risk', retry: 'Retry', empty: 'No stocks in this group', updated: 'Updated', support: 'Support', caution: 'Risk', disclaimer: 'For observation and risk reference only. Not investment advice.' }
    : { title: '自选股洞察', risk: '整体风险概览', retry: '重试', empty: '该分组暂无股票', updated: '更新时间', support: '支撑因素', caution: '风险因素', disclaimer: '仅供观察与风险参考，不构成投资建议。' };
  const groupLabels = locale === 'en'
    ? ['Priority', 'Watch', 'Cautious', 'Insufficient data']
    : ['重点关注', '继续观察', '谨慎关注', '数据不足'];
  const sortLabels = locale === 'en'
    ? ['Overall', 'Risk first', 'Data quality', 'Recent change']
    : ['综合参考', '风险优先', '数据完整度', '最近变化'];

  if (loading && !insights) return <View style={styles.panel}><ActivityIndicator color="#0F8B8D" /></View>;
  if (error && !insights) return (
    <View style={styles.errorCard}><AlertTriangle color="#B42318" size={20} /><Text style={styles.errorText}>{locale === 'en' ? 'Insights failed to load.' : '洞察加载失败，请重试。'}</Text><Pressable onPress={onRetry} style={styles.retry}><RefreshCcw color="#FFFFFF" size={14} /><Text style={styles.retryText}>{labels.retry}</Text></Pressable></View>
  );
  if (!insights) return null;

  const availableModes: WatchlistSortMode[] = insights.intelligence?.sort_modes?.length ? insights.intelligence.sort_modes : ['overall', 'risk', 'data_health', 'recent_change'];
  return (
    <View style={styles.panel}>
      <View style={styles.header}><Text style={styles.title}>{labels.title}</Text>{loading && <ActivityIndicator color="#0F8B8D" size="small" />}</View>
      <View style={styles.riskCard}><Text style={styles.cardTitle}>{labels.risk}</Text><Text style={styles.body}>{insights.risk_overview}</Text></View>
      <View style={styles.controls}>{availableModes.map((mode) => <Pressable key={mode} onPress={() => setSortMode(mode)} style={[styles.chip, sortMode === mode && styles.chipActive]}><Text style={[styles.chipText, sortMode === mode && styles.chipTextActive]}>{sortLabels[['overall', 'risk', 'data_health', 'recent_change'].indexOf(mode)]}</Text></Pressable>)}</View>
      <View style={styles.controls}>{groups.map((group, index) => <Pressable key={group} onPress={() => setActiveGroup(group)} style={[styles.groupChip, activeGroup === group && styles.groupChipActive]}><Text style={[styles.groupText, activeGroup === group && styles.groupTextActive]}>{groupLabels[index]} ({grouped[group].length})</Text></Pressable>)}</View>
      <View style={styles.cards}>{grouped[activeGroup].map((item) => (
        <Pressable key={item.code} onPress={() => onOpenStock(item.code)} style={styles.stockCard}>
          <View style={styles.stockHeader}><View><Text style={styles.stockName}>{item.name}</Text><Text style={styles.code}>{item.code} · {item.focus_label}</Text></View><ChevronRight color="#64748B" size={18} /></View>
          <Text style={styles.reason}>{item.focus_reason}</Text>
          {!!item.support_points.length && <Text style={styles.factor}><Text style={styles.support}>{labels.support}：</Text>{item.support_points.join('；')}</Text>}
          {!!item.risk_points.length && <Text style={styles.factor}><Text style={styles.risk}>{labels.caution}：</Text>{item.risk_points.join('；')}</Text>}
          <Text style={styles.meta}>{item.data_completeness}{item.updated_at ? ` · ${labels.updated} ${item.updated_at.replace('T', ' ').slice(0, 16)}` : ''}</Text>
        </Pressable>
      ))}{!grouped[activeGroup].length && <Text style={styles.empty}>{labels.empty}</Text>}</View>
      <Text style={styles.disclaimer}>{insights.disclaimer || labels.disclaimer}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  panel: { backgroundColor: '#FFFFFF', borderColor: '#DDE5EC', borderRadius: 18, borderWidth: 1, gap: 14, padding: 16 },
  header: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between' }, title: { color: '#162033', fontSize: 18, fontWeight: '800' },
  riskCard: { backgroundColor: '#FFF7ED', borderColor: '#FED7AA', borderRadius: 14, borderWidth: 1, gap: 6, padding: 14 }, cardTitle: { color: '#9A3412', fontSize: 14, fontWeight: '800' }, body: { color: '#4B5563', fontSize: 13, lineHeight: 20 },
  controls: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 }, chip: { backgroundColor: '#F1F5F9', borderRadius: 999, paddingHorizontal: 11, paddingVertical: 7 }, chipActive: { backgroundColor: '#0F8B8D' }, chipText: { color: '#475569', fontSize: 12, fontWeight: '700' }, chipTextActive: { color: '#FFFFFF' },
  groupChip: { borderBottomColor: 'transparent', borderBottomWidth: 2, paddingHorizontal: 4, paddingVertical: 7 }, groupChipActive: { borderBottomColor: '#0F8B8D' }, groupText: { color: '#64748B', fontSize: 12, fontWeight: '700' }, groupTextActive: { color: '#0F6E70' }, cards: { gap: 10 },
  stockCard: { backgroundColor: '#F8FAFC', borderColor: '#E2E8F0', borderRadius: 14, borderWidth: 1, gap: 7, padding: 13 }, stockHeader: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between' }, stockName: { color: '#162033', fontSize: 15, fontWeight: '800' }, code: { color: '#64748B', fontSize: 11, marginTop: 2 }, reason: { color: '#334155', fontSize: 13, lineHeight: 19 }, factor: { color: '#475569', fontSize: 12, lineHeight: 18 }, support: { color: '#087F5B', fontWeight: '800' }, risk: { color: '#B42318', fontWeight: '800' }, meta: { color: '#94A3B8', fontSize: 10 }, empty: { color: '#94A3B8', paddingVertical: 16, textAlign: 'center' }, disclaimer: { color: '#94A3B8', fontSize: 10, lineHeight: 15 },
  errorCard: { alignItems: 'center', backgroundColor: '#FEF3F2', borderColor: '#FECDCA', borderRadius: 14, borderWidth: 1, flexDirection: 'row', gap: 10, padding: 14 }, errorText: { color: '#B42318', flex: 1, fontSize: 12 }, retry: { alignItems: 'center', backgroundColor: '#B42318', borderRadius: 8, flexDirection: 'row', gap: 5, paddingHorizontal: 10, paddingVertical: 7 }, retryText: { color: '#FFFFFF', fontSize: 12, fontWeight: '800' },
});
