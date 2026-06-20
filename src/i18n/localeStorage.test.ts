import { getStoredLocale, saveStoredLocale } from './localeStorage';

function assertDoesNotThrow(label: string, fn: () => void) {
  try {
    fn();
  } catch (error) {
    throw new Error(`${label} threw: ${String(error)}`);
  }
}

const originalWindow = globalThis.window;

Object.defineProperty(globalThis, 'window', {
  configurable: true,
  value: {},
});

assertDoesNotThrow('getStoredLocale without localStorage', () => {
  if (getStoredLocale() !== null) {
    throw new Error('expected no stored locale');
  }
});

assertDoesNotThrow('saveStoredLocale without localStorage', () => {
  saveStoredLocale('en');
});

Object.defineProperty(globalThis, 'window', {
  configurable: true,
  value: originalWindow,
});
