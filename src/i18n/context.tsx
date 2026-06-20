import React, { createContext, useContext, useState, useEffect, type ReactNode } from 'react';
import type { Locale, TranslationSchema } from './types';
import { zh } from './locales/zh';
import { zhHant } from './locales/zh-Hant';
import { en } from './locales/en';
import { getStoredLocale, saveStoredLocale } from './localeStorage';

interface I18nContextType {
  locale: Locale;
  t: TranslationSchema;
  setLocale: (locale: Locale) => void;
}

const I18nContext = createContext<I18nContextType | null>(null);

const translations: Record<Locale, TranslationSchema> = {
  zh,
  'zh-Hant': zhHant,
  en,
};

export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(() => getStoredLocale() ?? 'zh');

  useEffect(() => {
    saveStoredLocale(locale);
  }, [locale]);

  const setLocale = (newLocale: Locale) => {
    setLocaleState(newLocale);
  };

  const t = translations[locale];

  return (
    <I18nContext.Provider value={{ locale, t, setLocale }}>
      {children}
    </I18nContext.Provider>
  );
}

export function useTranslation(): I18nContextType {
  const context = useContext(I18nContext);
  if (!context) {
    throw new Error('useTranslation must be used within an I18nProvider');
  }
  return context;
}

export function useTranslateSignal(signal: string): string {
  const { t } = useTranslation();
  return t.signal[signal as keyof typeof t.signal] || signal;
}

export function useTranslateRisk(risk: string): string {
  const { t } = useTranslation();
  return t.risk[risk as keyof typeof t.risk] || risk;
}

export function useTranslateAction(action: string): string {
  const { t } = useTranslation();
  return t.action[action as keyof typeof t.action] || action;
}
