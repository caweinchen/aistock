
import { Platform } from 'react-native';

let publicKey: string | null = null;

export async function fetchPublicKey(): Promise<string> {
  if (publicKey) return publicKey;
  
  let baseUrl: string;
  try {
    const { getApiBaseUrl } = await import('../services/storage');
    baseUrl = getApiBaseUrl();
  } catch (e) {
    baseUrl = Platform.OS === 'android' ? 'http://10.0.2.2:8000' : 'http://127.0.0.1:8000';
  }

  const response = await fetch(`${baseUrl}/api/auth/public-key`);
  if (!response.ok) {
    throw new Error('Failed to fetch public key');
  }
  const data = await response.json();
  publicKey = data.public_key;
  return publicKey;
}

function importPublicKey(pemKey: string): Promise<CryptoKey> {
  const key = pemKey
    .replace(/-----BEGIN PUBLIC KEY-----/, '')
    .replace(/-----END PUBLIC KEY-----/, '')
    .replace(/\s+/g, '');
  
  const binaryKey = base64ToArrayBuffer(key);
  
  return window.crypto.subtle.importKey(
    'spki',
    binaryKey,
    {
      name: 'RSA-OAEP',
      hash: 'SHA-256',
    },
    true,
    ['encrypt']
  );
}

function base64ToArrayBuffer(base64: string): ArrayBuffer {
  const binaryString = atob(base64);
  const length = binaryString.length;
  const bytes = new Uint8Array(length);
  for (let i = 0; i < length; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }
  return bytes.buffer;
}

function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  return btoa(String.fromCharCode(...bytes));
}

export async function encryptPassword(password: string): Promise<string> {
  const pemKey = await fetchPublicKey();
  const cryptoKey = await importPublicKey(pemKey);
  const encodedPassword = new TextEncoder().encode(password);
  const encrypted = await window.crypto.subtle.encrypt(
    { name: 'RSA-OAEP' },
    cryptoKey,
    encodedPassword
  );
  return `encrypted:${arrayBufferToBase64(encrypted)}`;
}