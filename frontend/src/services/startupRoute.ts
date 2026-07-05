import { getOfflineToken, isLoggedIn as hasAuthToken } from './storage';

export type StartupScreen = 'login' | 'home';

export interface StartupRouteState {
  isLoggedIn: boolean;
  currentScreen: StartupScreen;
}

export function getStartupRouteState(): StartupRouteState {
  const hasLocalSession = hasAuthToken() || !!getOfflineToken();

  return {
    isLoggedIn: hasLocalSession,
    currentScreen: hasLocalSession ? 'home' : 'login',
  };
}
