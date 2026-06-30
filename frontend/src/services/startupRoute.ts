export type StartupScreen = 'login';

export interface StartupRouteState {
  isLoggedIn: false;
  currentScreen: StartupScreen;
}

export function getStartupRouteState(): StartupRouteState {
  return {
    isLoggedIn: false,
    currentScreen: 'login',
  };
}
