import { getStoredLocale, saveStoredLocale } from './localeStorage';
import { afterEach, describe, expect, it } from 'vitest';

const originalWindow = globalThis.window;

describe('localeStorage', () => {
  afterEach(() => {
    Object.defineProperty(globalThis, 'window', {
      configurable: true,
      value: originalWindow,
    });
  });

  it('returns null without localStorage', () => {
    Object.defineProperty(globalThis, 'window', {
      configurable: true,
      value: {},
    });

    expect(getStoredLocale()).toBeNull();
  });

  it('ignores save without localStorage', () => {
    Object.defineProperty(globalThis, 'window', {
      configurable: true,
      value: {},
    });

    expect(() => saveStoredLocale('en')).not.toThrow();
  });
});
