import { Platform } from 'react-native';

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
  host: Platform.OS === 'android' ? '10.0.2.2' : '127.0.0.1',
  port: 8000,
};
// Try to dynamically require AsyncStorage in native environments.
let AsyncStorage: any | null = null;
try {
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  const mod = require('@react-native-async-storage/async-storage');
  AsyncStorage = mod && (mod.default || mod);
} catch (e) {
  AsyncStorage = null;
}

// In-memory cache so synchronous getters keep working the same as before.
let CACHE_SERVER_CONFIG: ServerConfig = DEFAULT_CONFIG;
let CACHE_AUTH_TOKEN: string | null = null;
let CACHE_USER_ID: string | null = null;
let CACHE_USERNAME: string | null = null;

function normalizeServerConfig(config: Partial<ServerConfig> | null | undefined): ServerConfig {
  const host = typeof config?.host === 'string' && config.host.trim() ? config.host.trim() : DEFAULT_CONFIG.host;
  const port = Number.isFinite(config?.port) ? Number(config?.port) : DEFAULT_CONFIG.port;
  return {
    host,
    port: Number.isInteger(port) && port > 0 ? port : DEFAULT_CONFIG.port,
  };
}

export async function initStorage(): Promise<void> {
  // Load persisted values into cache when running in native with AsyncStorage.
  if (AsyncStorage) {
    try {
      const keys = [
        STORAGE_KEYS.SERVER_CONFIG,
        STORAGE_KEYS.AUTH_TOKEN,
        STORAGE_KEYS.USER_ID,
        STORAGE_KEYS.USERNAME,
      ];
      const results = await AsyncStorage.multiGet(keys);
      const map: Record<string, string | null> = {};
      results.forEach(([k, v]: [string, string | null]) => {
        map[k] = v;
      });
      if (map[STORAGE_KEYS.SERVER_CONFIG]) {
        try {
          CACHE_SERVER_CONFIG = normalizeServerConfig(JSON.parse(map[STORAGE_KEYS.SERVER_CONFIG] as string) as ServerConfig);
        } catch {
          CACHE_SERVER_CONFIG = DEFAULT_CONFIG;
        }
      }
      CACHE_AUTH_TOKEN = map[STORAGE_KEYS.AUTH_TOKEN] ?? null;
      CACHE_USER_ID = map[STORAGE_KEYS.USER_ID] ?? null;
      CACHE_USERNAME = map[STORAGE_KEYS.USERNAME] ?? null;
    } catch {
      // ignore and keep defaults
    }
  }
}

export function getServerConfig(): ServerConfig {
  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      const stored = window.localStorage.getItem(STORAGE_KEYS.SERVER_CONFIG);
      if (stored) {
        return normalizeServerConfig(JSON.parse(stored) as ServerConfig);
      }
      return DEFAULT_CONFIG;
    }
    // native path: return cached value (initStorage should be called at app start)
    return normalizeServerConfig(CACHE_SERVER_CONFIG);
  } catch (e) {
    return DEFAULT_CONFIG;
  }
}

export function setServerConfig(config: ServerConfig): void {
  try {
    const normalizedConfig = normalizeServerConfig(config);
    CACHE_SERVER_CONFIG = normalizedConfig;
    if (typeof window !== 'undefined' && window.localStorage) {
      window.localStorage.setItem(STORAGE_KEYS.SERVER_CONFIG, JSON.stringify(normalizedConfig));
    } else if (AsyncStorage) {
      AsyncStorage.setItem(STORAGE_KEYS.SERVER_CONFIG, JSON.stringify(normalizedConfig)).catch(() => {});
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
    return CACHE_AUTH_TOKEN;
  } catch {
    return null;
  }
}

export function setAuthToken(token: string): void {
  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      window.localStorage.setItem(STORAGE_KEYS.AUTH_TOKEN, token);
    } else if (AsyncStorage) {
      AsyncStorage.setItem(STORAGE_KEYS.AUTH_TOKEN, token).catch(() => {});
      CACHE_AUTH_TOKEN = token;
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
    } else if (AsyncStorage) {
      AsyncStorage.multiRemove([STORAGE_KEYS.AUTH_TOKEN, STORAGE_KEYS.USER_ID]).catch(() => {});
      CACHE_AUTH_TOKEN = null;
      CACHE_USER_ID = null;
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
    return CACHE_USER_ID;
  } catch {
    return null;
  }
}

export function setUserId(userId: string): void {
  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      window.localStorage.setItem(STORAGE_KEYS.USER_ID, userId);
    } else if (AsyncStorage) {
      AsyncStorage.setItem(STORAGE_KEYS.USER_ID, userId).catch(() => {});
      CACHE_USER_ID = userId;
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
    return CACHE_USERNAME;
  } catch {
    return null;
  }
}

export function setStoredUser(username: string): void {
  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      window.localStorage.setItem(STORAGE_KEYS.USERNAME, username);
    } else if (AsyncStorage) {
      AsyncStorage.setItem(STORAGE_KEYS.USERNAME, username).catch(() => {});
      CACHE_USERNAME = username;
    }
  } catch {
    // Silent fail for storage errors
  }
}