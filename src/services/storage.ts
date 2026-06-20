const STORAGE_KEYS = {
  AUTH_TOKEN: 'auth_token',
  USER_ID: 'user_id',
  USERNAME: 'username',
  WATCHLIST: 'watchlist',
  PREFERENCES: 'preferences',
  SERVER_CONFIG: 'server_config',
};

export interface ServerConfig {
  host: string;
  port: number;
}

const DEFAULT_CONFIG: ServerConfig = {
  host: '127.0.0.1',
  port: 8000,
};

export function getServerConfig(): ServerConfig {
  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      const stored = window.localStorage.getItem(STORAGE_KEYS.SERVER_CONFIG);
      if (stored) {
        return JSON.parse(stored) as ServerConfig;
      }
    }
    return DEFAULT_CONFIG;
  } catch {
    return DEFAULT_CONFIG;
  }
}

export function setServerConfig(config: ServerConfig): void {
  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      window.localStorage.setItem(STORAGE_KEYS.SERVER_CONFIG, JSON.stringify(config));
    }
  } catch {
    // Silent fail for storage errors
  }
}

export function getApiBaseUrl(): string {
  const config = getServerConfig();
  return `http://${config.host}:${config.port}`;
}

export function getAuthToken(): string | null {
  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      return window.localStorage.getItem(STORAGE_KEYS.AUTH_TOKEN);
    }
    return null;
  } catch {
    return null;
  }
}

export function setAuthToken(token: string): void {
  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      window.localStorage.setItem(STORAGE_KEYS.AUTH_TOKEN, token);
    }
  } catch {
    // Silent fail for storage errors
  }
}

export function clearAuthToken(): void {
  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      window.localStorage.removeItem(STORAGE_KEYS.AUTH_TOKEN);
      window.localStorage.removeItem(STORAGE_KEYS.USER_ID);
    }
  } catch {
    // Silent fail for storage errors
  }
}

export function getUserId(): string | null {
  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      return window.localStorage.getItem(STORAGE_KEYS.USER_ID);
    }
    return null;
  } catch {
    return null;
  }
}

export function setUserId(userId: string): void {
  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      window.localStorage.setItem(STORAGE_KEYS.USER_ID, userId);
    }
  } catch {
    // Silent fail for storage errors
  }
}

export function isLoggedIn(): boolean {
  const token = getAuthToken();
  return !!token;
}

export function getStoredUser(): string | null {
  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      return window.localStorage.getItem(STORAGE_KEYS.USERNAME);
    }
    return null;
  } catch {
    return null;
  }
}

export function setStoredUser(username: string): void {
  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      window.localStorage.setItem(STORAGE_KEYS.USERNAME, username);
    }
  } catch {
    // Silent fail for storage errors
  }
}