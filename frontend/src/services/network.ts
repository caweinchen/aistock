import { Platform } from 'react-native';

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

export async function checkNetwork(): Promise<NetworkStatus> {
  if (NetInfo) {
    try {
      const state = await NetInfo.fetch();
      currentStatus = state.isConnected === true ? 'online' : state.isConnected === false ? 'offline' : 'unknown';
      return currentStatus;
    } catch {
      currentStatus = 'unknown';
    }
  }
  
  if (typeof navigator !== 'undefined' && navigator.onLine !== undefined) {
    currentStatus = navigator.onLine ? 'online' : 'offline';
    return currentStatus;
  }
  
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