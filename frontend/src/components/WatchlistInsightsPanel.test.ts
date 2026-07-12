import { describe, expect, it } from 'vitest';
import type { WatchlistStockInsight } from '../types';
import { groupInsights, sortInsights } from '../services/watchlistInsights';

const insight = (overrides: Partial<WatchlistStockInsight>): WatchlistStockInsight => ({
  code: 'A', name: 'A', focus_level: 'watch', focus_label: '继续观察', focus_reason: '观察',
  support_points: [], risk_points: [], data_completeness: 'complete', score: 60,
  risk_score: 10, priority_score: 10, updated_at: '2026-07-10T00:00:00Z', ...overrides,
});

const items = [
  insight({ code: 'priority', priority_score: 90, risk_score: 20, data_completeness: 'mostly_complete', updated_at: '2026-07-09T00:00:00Z' }),
  insight({ code: 'risk', priority_score: 30, risk_score: 95, data_completeness: 'incomplete', updated_at: '2026-07-11T00:00:00Z' }),
  insight({ code: 'complete', priority_score: 20, risk_score: 10, data_completeness: 'complete', updated_at: '2026-07-08T00:00:00Z' }),
  insight({ code: 'recent', priority_score: 10, risk_score: 5, data_completeness: 'insufficient', updated_at: '2026-07-12T00:00:00Z' }),
];

describe('sortInsights', () => {
  it('sorts by comprehensive priority', () => expect(sortInsights(items, 'overall')[0].code).toBe('priority'));
  it('sorts highest risk first', () => expect(sortInsights(items, 'risk')[0].code).toBe('risk'));
  it('sorts most complete data first', () => expect(sortInsights(items, 'data_health')[0].code).toBe('complete'));
  it('sorts most recently changed first', () => expect(sortInsights(items, 'recent_change')[0].code).toBe('recent'));
});

describe('groupInsights', () => {
  it('always returns all four focus groups', () => {
    const grouped = groupInsights([insight({ focus_level: 'priority' })]);
    expect(grouped.priority).toHaveLength(1);
    expect(grouped.watch).toEqual([]);
    expect(grouped.cautious).toEqual([]);
    expect(grouped.insufficient_data).toEqual([]);
  });
});
