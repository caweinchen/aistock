import { getApiBaseUrl } from './storage';

let NetInfo: any | null = null;
try {
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  const mod = require('@react-native-community/netinfo');
  NetInfo = mod && (mod.default || mod);
} catch (e) {
  NetInfo = null;
}

export type NetworkStatus = 'online' | 'offline' | 'unknown';

let currentStatus: NetworkStatus = 'unknown';
const listeners = new Set<(status: NetworkStatus) => void>();

export function getNetworkStatus(): NetworkStatus {
  return currentStatus;
}

export function isOnline(): boolean {
  return currentStatus === 'online';
}

export function isOffline(): boolean {
  return currentStatus === 'offline';
}

export function isNetworkFailure(err: unknown): boolean {
  if (!(err instanceof TypeError)) return false;

  const message = err.message.toLowerCase();
  return (
    message.includes('fetch') ||
    message.includes('network request failed') ||
    message.includes('networkerror') ||
    message.includes('failed to fetch') ||
    message.includes('load failed')
  );
}

export function addNetworkListener(callback: (status: NetworkStatus) => void): () => void {
  listeners.add(callback);
  
  if (NetInfo) {
    NetInfo.addEventListener((state: any) => {
      const status = state.isConnected === true ? 'online' : state.isConnected === false ? 'offline' : 'unknown';
      currentStatus = status;
      listeners.forEach(listener => listener(status));
    });
  }
  
  return () => {
    listeners.delete(callback);
  };
}

async function checkBackendHealth(timeoutMs = 3000): Promise<boolean> {
  if (typeof fetch === 'undefined') return currentStatus === 'online';

  const controller = typeof AbortController !== 'undefined' ? new AbortController() : null;
  const timeoutId = controller
    ? setTimeout(() => controller.abort(), timeoutMs)
    : null;

  try {
    const response = await fetch(`${getApiBaseUrl()}/api/health`, {
      method: 'GET',
      cache: 'no-store',
      signal: controller?.signal,
    });
    return response.ok;
  } catch {
    return false;
  } finally {
    if (timeoutId) clearTimeout(timeoutId);
  }
}

export async function checkNetwork(): Promise<NetworkStatus> {
  let deviceStatus: NetworkStatus = 'unknown';

  if (NetInfo) {
    try {
      const state = await NetInfo.fetch();
      deviceStatus = state.isConnected === true ? 'online' : state.isConnected === false ? 'offline' : 'unknown';
    } catch {
      deviceStatus = 'unknown';
    }
  }
  
  if (deviceStatus === 'unknown' && typeof navigator !== 'undefined' && navigator.onLine !== undefined) {
    deviceStatus = navigator.onLine ? 'online' : 'offline';
  }

  if (deviceStatus === 'offline') {
    currentStatus = 'offline';
    return currentStatus;
  }

  const backendOnline = await checkBackendHealth();
  currentStatus = backendOnline ? 'online' : 'offline';
  return currentStatus;
}

export async function waitForNetwork(timeout = 30000): Promise<boolean> {
  return new Promise((resolve) => {
    if (isOnline()) {
      resolve(true);
      return;
    }
    
    const timeoutId = setTimeout(() => {
      unsubscribe();
      resolve(false);
    }, timeout);
    
    const unsubscribe = addNetworkListener((status) => {
      if (status === 'online') {
        clearTimeout(timeoutId);
        unsubscribe();
        resolve(true);
      }
    });
  });
}
