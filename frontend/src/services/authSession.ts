import { getOfflineToken, isLoggedIn } from './storage';

export function getInitialAuthState(): boolean {
  return isLoggedIn() || !!getOfflineToken();
}
