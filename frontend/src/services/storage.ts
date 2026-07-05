import { Platform } from 'react-native';

// ============================================
// Storage Layer - Unified native + web storage
// ============================================

const STORAGE_KEYS = {
  AUTH_TOKEN: 'auth_token',
  USER_ID: 'user_id',
  USERNAME: 'username',
  USER_ROLE: 'user_role',
  PASSWORD_HASH: 'password_hash',
  OFFLINE_TOKEN: 'offline_token',
  WATCHLIST: 'watchlist',
  PREFERENCES: 'preferences',
  SERVER_CONFIG: 'server_config',
  // Cache keys for localDb
  CACHE_PREFIX: 'cache_',
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
let CACHE_USER_ROLE: string | null = null;
let CACHE_PASSWORD_HASH: string | null = null;
let CACHE_OFFLINE_TOKEN: string | null = null;

// ============================================
// Unified Storage API (used by localDb)
// ============================================

export const storage = {
  async getItem(key: string): Promise<string | null> {
    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        return window.localStorage.getItem(key);
      }
      if (AsyncStorage) {
        return await AsyncStorage.getItem(key);
      }
      return null;
    } catch {
      return null;
    }
  },

  async setItem(key: string, value: string): Promise<void> {
    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        window.localStorage.setItem(key, value);
        return;
      }
      if (AsyncStorage) {
        await AsyncStorage.setItem(key, value);
      }
    } catch {
      // Silent fail
    }
  },

  async removeItem(key: string): Promise<void> {
    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        window.localStorage.removeItem(key);
        return;
      }
      if (AsyncStorage) {
        await AsyncStorage.removeItem(key);
      }
    } catch {
      // Silent fail
    }
  },

  async multiGet(keys: string[]): Promise<Record<string, string | null>> {
    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        const result: Record<string, string | null> = {};
        keys.forEach(key => {
          result[key] = window.localStorage.getItem(key);
        });
        return result;
      }
      if (AsyncStorage) {
        const results = await AsyncStorage.multiGet(keys);
        const result: Record<string, string | null> = {};
        results.forEach(([k, v]: [string, string | null]) => {
          result[k] = v;
        });
        return result;
      }
      return {};
    } catch {
      return {};
    }
  },

  async multiRemove(keys: string[]): Promise<void> {
    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        keys.forEach(key => window.localStorage.removeItem(key));
        return;
      }
      if (AsyncStorage) {
        await AsyncStorage.multiRemove(keys);
      }
    } catch {
      // Silent fail
    }
  },

  async getAllKeys(): Promise<string[]> {
    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        return Object.keys(window.localStorage);
      }
      if (AsyncStorage) {
        return await AsyncStorage.getAllKeys();
      }
      return [];
    } catch {
      return [];
    }
  },

  async clear(): Promise<void> {
    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        window.localStorage.clear();
        return;
      }
      if (AsyncStorage) {
        await AsyncStorage.clear();
      }
    } catch {
      // Silent fail
    }
  },
};

export { STORAGE_KEYS, storage as defaultStorage };

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
        STORAGE_KEYS.USER_ROLE,
        STORAGE_KEYS.PASSWORD_HASH,
        STORAGE_KEYS.OFFLINE_TOKEN,
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
      CACHE_USER_ROLE = map[STORAGE_KEYS.USER_ROLE] ?? null;
      CACHE_PASSWORD_HASH = map[STORAGE_KEYS.PASSWORD_HASH] ?? null;
      CACHE_OFFLINE_TOKEN = map[STORAGE_KEYS.OFFLINE_TOKEN] ?? null;
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
      window.localStorage.removeItem(STORAGE_KEYS.USER_ROLE);
      window.localStorage.removeItem(STORAGE_KEYS.OFFLINE_TOKEN);
    } else if (AsyncStorage) {
      AsyncStorage.multiRemove([
        STORAGE_KEYS.AUTH_TOKEN,
        STORAGE_KEYS.USER_ID,
        STORAGE_KEYS.USER_ROLE,
        STORAGE_KEYS.OFFLINE_TOKEN,
      ]).catch(() => {});
      CACHE_AUTH_TOKEN = null;
      CACHE_USER_ID = null;
      CACHE_USER_ROLE = null;
      CACHE_OFFLINE_TOKEN = null;
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

// ============================================
// Offline Login Support
// ============================================

async function hashPassword(password: string): Promise<string> {
  try {
    if (typeof crypto !== 'undefined' && crypto.subtle) {
      const encoder = new TextEncoder();
      const data = encoder.encode(password);
      const hashBuffer = await crypto.subtle.digest('SHA-256', data);
      const hashArray = Array.from(new Uint8Array(hashBuffer));
      return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
    }
    // Fallback: simple hash (not cryptographically secure but works offline)
    let hash = 0;
    for (let i = 0; i < password.length; i++) {
      const char = password.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash;
    }
    return `fb_${Math.abs(hash).toString(16)}`;
  } catch {
    return `fb_${password.length}`;
  }
}

export async function savePasswordForOffline(username: string, password: string): Promise<void> {
  try {
    const hash = await hashPassword(password);
    const data = JSON.stringify({ username, hash });
    if (typeof window !== 'undefined' && window.localStorage) {
      window.localStorage.setItem(STORAGE_KEYS.PASSWORD_HASH, data);
    } else if (AsyncStorage) {
      await AsyncStorage.setItem(STORAGE_KEYS.PASSWORD_HASH, data);
      CACHE_PASSWORD_HASH = data;
    }
  } catch {
    // Silent fail
  }
}

export async function verifyOfflineLogin(username: string, password: string): Promise<boolean> {
  try {
    let storedData: string | null = null;
    if (typeof window !== 'undefined' && window.localStorage) {
      storedData = window.localStorage.getItem(STORAGE_KEYS.PASSWORD_HASH);
    } else {
      storedData = CACHE_PASSWORD_HASH;
    }
    if (!storedData) return false;
    
    const { username: storedUsername, hash: storedHash } = JSON.parse(storedData) as { username: string; hash: string };
    if (storedUsername !== username) return false;
    
    const inputHash = await hashPassword(password);
    return inputHash === storedHash;
  } catch {
    return false;
  }
}

export function hasOfflineLogin(): boolean {
  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      return !!window.localStorage.getItem(STORAGE_KEYS.PASSWORD_HASH);
    }
    return !!CACHE_PASSWORD_HASH;
  } catch {
    return false;
  }
}

export function setOfflineToken(token: string): void {
  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      window.localStorage.setItem(STORAGE_KEYS.OFFLINE_TOKEN, token);
    } else if (AsyncStorage) {
      AsyncStorage.setItem(STORAGE_KEYS.OFFLINE_TOKEN, token).catch(() => {});
      CACHE_OFFLINE_TOKEN = token;
    }
  } catch {
    // Silent fail
  }
}

export function getOfflineToken(): string | null {
  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      return window.localStorage.getItem(STORAGE_KEYS.OFFLINE_TOKEN);
    }
    return CACHE_OFFLINE_TOKEN;
  } catch {
    return null;
  }
}

export function clearOfflineLogin(): void {
  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      window.localStorage.removeItem(STORAGE_KEYS.PASSWORD_HASH);
      window.localStorage.removeItem(STORAGE_KEYS.OFFLINE_TOKEN);
    } else if (AsyncStorage) {
      AsyncStorage.multiRemove([STORAGE_KEYS.PASSWORD_HASH, STORAGE_KEYS.OFFLINE_TOKEN]).catch(() => {});
      CACHE_PASSWORD_HASH = null;
      CACHE_OFFLINE_TOKEN = null;
    }
  } catch {
    // Silent fail
  }
}

export function getStoredUserRole(): string | null {
  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      return window.localStorage.getItem(STORAGE_KEYS.USER_ROLE);
    }
    return CACHE_USER_ROLE;
  } catch {
    return null;
  }
}

export function setStoredUserRole(role: string): void {
  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      window.localStorage.setItem(STORAGE_KEYS.USER_ROLE, role);
    } else if (AsyncStorage) {
      AsyncStorage.setItem(STORAGE_KEYS.USER_ROLE, role).catch(() => {});
      CACHE_USER_ROLE = role;
    }
  } catch {
    // Silent fail for storage errors
  }
}
