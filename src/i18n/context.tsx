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

// 翻译策略名称
export function useTranslateStrategyName(name: string): string {
  const { t } = useTranslation();
  const strategyMap: Record<string, keyof typeof t.strategy> = {
    'Trend Breakout': 'trendBreakout',
    'Low Valuation Reversal': 'lowValuationReversal',
    'Dividend Defense': 'dividendDefense',
  };
  const key = strategyMap[name];
  return key ? t.strategy[key] : name;
}

// 翻译策略规则
export function useTranslateRule(rule: string): string {
  const { t } = useTranslation();
  const ruleMap: Record<string, keyof typeof t.strategy> = {
    'Buy when close crosses above the 20-day moving average.': 'ruleTrendBreakout1',
    'Sell when close falls below the 20-day moving average or stop-loss is triggered.': 'ruleTrendBreakout2',
    'Volume expansion strengthens the breakout reason when available.': 'ruleTrendBreakout3',
    'Buy when price recovers from the recent low range.': 'ruleLowValuation1',
    'Sell when price reverts toward the recent high range or stop-loss is triggered.': 'ruleLowValuation2',
    'Use recent price range as a valuation proxy until valuation data is available.': 'ruleLowValuation3',
    'Buy only when trend is stable and realized volatility is moderate.': 'ruleDividend1',
    'Sell when trend weakens, volatility rises, or stop-loss is triggered.': 'ruleDividend2',
    'Use defensive price behavior as a dividend proxy until dividend data is available.': 'ruleDividend3',
  };
  const key = ruleMap[rule];
  return key ? t.strategy[key] : rule;
}

// 翻译交易原因
export function useTranslateReason(reason: string): string {
  const { t } = useTranslation();
  const reasonMap: Record<string, keyof typeof t.strategy> = {
    'Close crossed above the 20-day moving average.': 'reasonCrossAbove',
    'Close fell below the 20-day moving average or stop-loss was hit.': 'reasonCrossBelow',
    'Price recovered from the recent low range.': 'reasonRecoverLow',
    'Price reverted toward the recent high range or stop-loss was hit.': 'reasonRevertHigh',
    'Trend was stable with moderate realized volatility.': 'reasonStableTrend',
    'Trend weakened, volatility rose, or stop-loss was hit.': 'reasonTrendWeak',
    'Closed open position at the end of the backtest.': 'reasonClosePosition',
  };
  const key = reasonMap[reason];
  return key ? t.strategy[key] : reason;
}
