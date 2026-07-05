import type { ResearchSnapshot } from '../types';

interface SessionResetState {
  isSearchVisible: boolean;
  pendingSearchQuery: string | null;
  refreshKey: number;
  researchSnapshot: ResearchSnapshot | null;
  screenParams: Record<string, never>;
  searchQuery: string;
  selectedStockCode: undefined;
}

export function createUserSessionKey(username: string | null, userId: string | null): string {
  return `${username ?? 'anonymous'}:${userId ?? '0'}`;
}

export function createSessionResetState(currentRefreshKey: number): SessionResetState {
  return {
    isSearchVisible: false,
    pendingSearchQuery: null,
    refreshKey: currentRefreshKey + 1,
    researchSnapshot: null,
    screenParams: {},
    searchQuery: '',
    selectedStockCode: undefined,
  };
}
