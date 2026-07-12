import type { WatchlistFocusLevel, WatchlistSortMode, WatchlistStockInsight } from '../types';

const completenessRank = { complete: 4, mostly_complete: 3, incomplete: 2, insufficient: 1 } as const;

export function sortInsights(items: WatchlistStockInsight[], mode: WatchlistSortMode): WatchlistStockInsight[] {
  return [...items].sort((a, b) => {
    if (mode === 'risk') return b.risk_score - a.risk_score;
    if (mode === 'data_health') return completenessRank[b.data_completeness] - completenessRank[a.data_completeness];
    if (mode === 'recent_change') return Date.parse(b.updated_at ?? '') - Date.parse(a.updated_at ?? '');
    return b.priority_score - a.priority_score;
  });
}

export function groupInsights(items: WatchlistStockInsight[]): Record<WatchlistFocusLevel, WatchlistStockInsight[]> {
  return items.reduce<Record<WatchlistFocusLevel, WatchlistStockInsight[]>>((result, item) => {
    result[item.focus_level].push(item);
    return result;
  }, { priority: [], watch: [], cautious: [], insufficient_data: [] });
}
