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

type TranslationKey = keyof TranslationSchema;
type NestedKey<T extends TranslationKey> = keyof TranslationSchema[T] & string;

const factorLabelMap: Record<string, NestedKey<'factor'>> = {
  capital_flow: 'capitalFlow',
  'Capital Flow': 'capitalFlow',
  资金流向: 'capitalFlow',
  valuation: 'valuation',
  Valuation: 'valuation',
  估值水平: 'valuation',
  momentum: 'momentum',
  Momentum: 'momentum',
  动量指标: 'momentum',
  volatility: 'volatility',
  Volatility: 'volatility',
  波动性: 'volatility',
  profitability: 'profitability',
  Profitability: 'profitability',
  盈利能力: 'profitability',
};

const factorDescriptionMap: Record<string, NestedKey<'factor'>> = {
  'Strong capital inflow detected.': 'capitalFlowStrong',
  'Mixed capital flow.': 'capitalFlowMixed',
  'Capital outflow detected.': 'capitalFlowOutflow',
  'Strong upward momentum.': 'valuationStrongMomentum',
  'Reasonable valuation.': 'valuationReasonable',
  'Below average valuation.': 'valuationBelowAverage',
  'Strong momentum.': 'momentumStrong',
  'Weak momentum.': 'momentumWeak',
  'Negative momentum.': 'momentumNegative',
  'High volatility.': 'volatilityHigh',
  'Moderate volatility.': 'volatilityModerate',
  'Low volatility.': 'volatilityLow',
  'Strong institutional interest.': 'capitalFlowInstitutional',
  'Slightly undervalued.': 'valuationSlightlyUndervalued',
  'Healthy upward trend.': 'momentumHealthyUpward',
  '近5日主力资金净流入。': 'capitalFlowFiveDayInflow',
  '资金流向稳定。': 'capitalFlowStable',
  '近期资金大幅净流入。': 'capitalFlowRecentLargeInflow',
  '估值处于行业中上水平。': 'valuationAboveIndustry',
  '估值处于合理水平。': 'valuationReasonableLevel',
  '估值明显偏低。': 'valuationClearlyLow',
  '价格走势优于300只同类股票。': 'momentumOutperformPeers',
  '温和上涨动能。': 'momentumModerateRise',
  '上涨动能强劲。': 'momentumStrongRise',
  '短期波动性可控。': 'volatilityControlled',
  '波动在可接受范围内。': 'volatilityAcceptable',
  '波动适中。': 'volatilityModerateLevel',
};

const strategySummaryMap: Record<string, NestedKey<'strategy'>> = {
  'Stable dividend strategy suitable for conservative investors.': 'strategySummaryDividendStable',
  'Steady upward trend established.': 'strategySummarySteadyUpward',
  'Consistent dividend growth.': 'strategySummaryDividendGrowth',
  '趋势形态已形成，等待确认信号，不追高。': 'strategySummaryTrendWait',
  '低估特征明显，信心稳固。': 'strategySummaryLowValuation',
  '横盘整理阶段，等待方向性突破。': 'strategySummaryConsolidation',
  '估值优势存在，适合逢低吸纳。': 'strategySummaryBuyDip',
  '突破盘整格局。': 'strategySummaryBreakout',
  '分红稳定，收益率有吸引力。': 'strategySummaryDividendAttractive',
};

const alertTitleMap: Record<string, NestedKey<'alert'>> = {
  '估值提醒': 'valuationReminder',
  '估值过高风险': 'alertValuationHigh',
  '波动性风险': 'alertVolatility',
  '资金流出风险': 'alertCapitalOutflow',
  '盈利能力风险': 'alertProfitability',
  '价格下跌风险': 'alertPriceDrop',
  '短期涨幅过大': 'alertShortTermSurge',
  'Credit Risk': 'alertCreditRisk',
};

const alertMessageMap: Record<string, NestedKey<'alert'>> = {
  '当前市盈率38.5倍，高于历史平均水平。': 'valuationPeHigh',
  'Non-performing loan ratio slightly above sector average.': 'creditRiskNpl',
};

const instTypeMap: Record<string, NestedKey<'detail'>> = {
  基金: 'instFund',
  保险: 'instInsurance',
  券商: 'instBroker',
  QFII: 'instQfii',
  社保: 'instSocialSecurity',
  信托: 'instTrust',
  其他: 'instOther',
  Fund: 'instFund',
  Insurance: 'instInsurance',
  Broker: 'instBroker',
};

const dividendPlanMap: Record<string, NestedKey<'detail'>> = {
  实施: 'dividendImplemented',
  预案: 'dividendPlanDraft',
  股东大会通过: 'dividendApproved',
  取消: 'dividendCancelled',
  Implemented: 'dividendImplemented',
};

const newsSourceMap: Record<string, NestedKey<'detail'>> = {
  新浪财经: 'sourceSinaFinance',
  东方财富: 'sourceEastMoney',
  证券时报: 'sourceSecuritiesTimes',
  上证报: 'sourceShanghaiSecuritiesNews',
  Sina: 'sourceSinaFinance',
  Eastmoney: 'sourceEastMoney',
};

function translateMapped<T extends TranslationKey>(
  value: string,
  section: TranslationSchema[T],
  map: Record<string, NestedKey<T>>,
): string {
  const key = map[value];
  return key ? String(section[key]) : value;
}

export function translatePeriod(period: string, t: TranslationSchema): string {
  const lastBars = period.match(/^Last (\d+) bars$/);
  if (lastBars) {
    return t.strategy.lastBars.replace('{count}', lastBars[1]);
  }
  const lastDays = period.match(/^Last (\d+) days$/);
  if (lastDays) {
    return t.strategy.lastBars.replace('{count}', lastDays[1]);
  }
  const recentDays = period.match(/^近(\d+)天$/);
  if (recentDays) {
    return t.strategy.lastBars.replace('{count}', recentDays[1]);
  }
  const recentYear = period === '近1年' || period === 'Last 1 year';
  return recentYear ? t.strategy.lastYear : period;
}

export function translateFactorLabel(factorKey: string, label: string, t: TranslationSchema): string {
  return translateMapped(factorKey, t.factor, factorLabelMap) !== factorKey
    ? translateMapped(factorKey, t.factor, factorLabelMap)
    : translateMapped(label, t.factor, factorLabelMap);
}

export function translateFactorDescription(description: string, t: TranslationSchema): string {
  return translateMapped(description, t.factor, factorDescriptionMap);
}

export function translateAlertTitle(title: string, t: TranslationSchema): string {
  return translateMapped(title, t.alert, alertTitleMap);
}

export function translateAlertMessage(message: string, t: TranslationSchema): string {
  return translateMapped(message, t.alert, alertMessageMap);
}

export function translateStrategySummary(summary: string, t: TranslationSchema): string {
  const backtest = summary.match(/^(.+) backtest completed from (.+) to (.+)\.$/);
  if (backtest) {
    const strategyName = translateMapped(backtest[1], t.strategy, strategyMap);
    return t.strategy.backtestFrom
      .replace('{strategy}', strategyName)
      .replace('{start}', backtest[2])
      .replace('{end}', backtest[3]);
  }
  return translateMapped(summary, t.strategy, strategySummaryMap);
}

export function translateInstType(instType: string, t: TranslationSchema): string {
  return translateMapped(instType, t.detail, instTypeMap);
}

export function translateDividendPlan(plan: string, t: TranslationSchema): string {
  return translateMapped(plan, t.detail, dividendPlanMap);
}

export function translateNewsSource(source: string, t: TranslationSchema): string {
  return translateMapped(source, t.detail, newsSourceMap);
}

const strategyMap: Record<string, NestedKey<'strategy'>> = {
  'Trend Breakout': 'trendBreakout',
  趋势突破: 'trendBreakout',
  'Low Valuation Reversal': 'lowValuationReversal',
  低估值反转: 'lowValuationReversal',
  'Dividend Defense': 'dividendDefense',
  分红防御: 'dividendDefense',
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
  const key = strategyMap[name];
  return key ? t.strategy[key] : name;
}

export function useTranslateFactor() {
  const { t } = useTranslation();
  return {
    label: (factorKey: string, label: string) => translateFactorLabel(factorKey, label, t),
    description: (description: string) => translateFactorDescription(description, t),
  };
}

export function useTranslateAlert() {
  const { t } = useTranslation();
  return {
    title: (title: string) => translateAlertTitle(title, t),
    message: (message: string) => translateAlertMessage(message, t),
  };
}

export function useTranslateStrategySummary() {
  const { t } = useTranslation();
  return (summary: string) => translateStrategySummary(summary, t);
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
