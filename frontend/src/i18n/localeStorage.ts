import type { Locale } from './types';

const LOCALE_STORAGE_KEY = 'locale';
const SUPPORTED_LOCALES: Locale[] = ['zh', 'zh-Hant', 'en'];

function isLocale(value: string | null): value is Locale {
  return SUPPORTED_LOCALES.includes(value as Locale);
}

function getLocalStorage(): Storage | null {
  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      return window.localStorage;
    }
  } catch {
    return null;
  }
  return null;
}

export function getStoredLocale(): Locale | null {
  const storage = getLocalStorage();
  if (!storage) {
    return null;
  }

  const savedLocale = storage.getItem(LOCALE_STORAGE_KEY);
  return isLocale(savedLocale) ? savedLocale : null;
}

export function saveStoredLocale(locale: Locale): void {
  const storage = getLocalStorage();
  if (!storage) {
    return;
  }

  storage.setItem(LOCALE_STORAGE_KEY, locale);
}
