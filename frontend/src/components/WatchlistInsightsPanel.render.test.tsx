import React from 'react';
import { act, create, type ReactTestInstance } from 'react-test-renderer';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { WatchlistInsights } from '../types';

vi.mock('react-native', () => ({
  ActivityIndicator: 'ActivityIndicator', Pressable: 'Pressable', Text: 'Text', View: 'View',
  StyleSheet: { create: <T,>(styles: T) => styles },
}));
vi.mock('lucide-react-native', () => ({ AlertTriangle: 'AlertTriangle', ChevronRight: 'ChevronRight', RefreshCcw: 'RefreshCcw' }));

import { WatchlistInsightsPanel } from './WatchlistInsightsPanel';

declare global {
  var IS_REACT_ACT_ENVIRONMENT: boolean | undefined;
}

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

const base: WatchlistInsights = {
  total: 1,
  groups: { positive: [], watch: [], cautious: [], insufficient_data: [] },
  risk_overview: '波动风险偏高，请结合数据谨慎观察。',
  disclaimer: '不构成投资建议',
  intelligence: {
    radar: { title: '概览', summary: '摘要', priority_count: 0, cautious_count: 0, insufficient_count: 1 },
    observations: [], sort_modes: ['overall', 'risk', 'data_health', 'recent_change'],
    insights: [{ code: '000001', name: '示例股', focus_level: 'insufficient_data', focus_label: '数据不足', focus_reason: '关键指标缺失', support_points: ['估值稳定'], risk_points: ['数据过期'], data_completeness: 'insufficient', score: null, risk_score: 80, priority_score: 10, updated_at: '2026-07-13T10:00:00Z' }],
  },
};

const render = async (overrides: Partial<React.ComponentProps<typeof WatchlistInsightsPanel>> = {}) => {
  const props = { insights: base, loading: false, error: false, locale: 'zh', onRetry: vi.fn(), onRefresh: vi.fn(), onOpenStock: vi.fn(), ...overrides };
  let tree: ReturnType<typeof create>;
  await act(async () => { tree = create(<WatchlistInsightsPanel {...props} />); });
  return { root: tree!.root, props };
};

const press = async (node: ReactTestInstance) => { await act(async () => node.props.onPress()); };

describe('WatchlistInsightsPanel rendering and interactions', () => {
  beforeEach(() => vi.clearAllMocks());

  it('renders the overall risk card and data-insufficient stock', async () => {
    const { root } = await render();
    expect(root.findByProps({ accessibilityLabel: '整体风险概览' })).toBeTruthy();
    await press(root.findByProps({ accessibilityLabel: '筛选数据不足' }));
    expect(root.findByProps({ accessibilityLabel: '查看示例股详情' })).toBeTruthy();
  });

  it('retries after an API failure', async () => {
    const onRetry = vi.fn();
    const { root } = await render({ insights: null, error: true, onRetry });
    await press(root.findByProps({ accessibilityLabel: '重试加载洞察' }));
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it('opens stock details from an insight card', async () => {
    const onOpenStock = vi.fn();
    const { root } = await render({ onOpenStock });
    await press(root.findByProps({ accessibilityLabel: '筛选数据不足' }));
    await press(root.findByProps({ accessibilityLabel: '查看示例股详情' }));
    expect(onOpenStock).toHaveBeenCalledWith('000001');
  });

  it('offers refresh in the successful state', async () => {
    const onRefresh = vi.fn();
    const { root } = await render({ onRefresh });
    await press(root.findByProps({ accessibilityLabel: '刷新洞察' }));
    expect(onRefresh).toHaveBeenCalledOnce();
  });
});
