const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..', 'frontend');

function read(relativePath) {
  return fs.readFileSync(path.join(root, relativePath), 'utf8');
}

function assertIncludes(file, needle) {
  const source = read(file);
  if (!source.includes(needle)) {
    throw new Error(`${file} must include ${needle}`);
  }
}

function assertNotIncludes(file, needle) {
  const source = read(file);
  if (source.includes(needle)) {
    throw new Error(`${file} must not include ${needle}`);
  }
}

[
  'translateFactorLabel',
  'translateFactorDescription',
  'translateAlertTitle',
  'translateAlertMessage',
  'translateStrategySummary',
  'translateInstType',
  'translateDividendPlan',
  'translateNewsSource',
].forEach((name) => assertIncludes('src/i18n/context.tsx', name));

[
  'useTranslateFactor',
  'useTranslateAlert',
  'useTranslateStrategySummary',
  'translatePeriod',
  'translateInstType',
  'translateDividendPlan',
  'translateNewsSource',
].forEach((name) => assertIncludes('src/i18n/index.ts', name));

assertIncludes('src/components/FactorTile.tsx', 'useTranslateFactor');
assertIncludes('src/components/AlertCard.tsx', 'useTranslateAlert');
assertIncludes('src/components/StrategyCard.tsx', 'useTranslateStrategySummary');
assertIncludes('src/components/PriceChart.tsx', 't.chart.separator');
assertIncludes('src/pages/StockDetailScreen.tsx', 'translateInstType');
assertIncludes('src/pages/StockDetailScreen.tsx', 'translateDividendPlan');
assertIncludes('src/pages/StockDetailScreen.tsx', 'translateNewsSource');

assertNotIncludes('src/pages/StockDetailScreen.tsx', '>楼{record.div_cash.toFixed(4)}<');
assertNotIncludes('src/components/PriceChart.tsx', '${stock.name} · ${t.chart.last}');

[
  'src/i18n/locales/zh.ts',
  'src/i18n/locales/zh-Hant.ts',
  'src/i18n/locales/en.ts',
].forEach((file) => {
  [
    'capitalFlowStrong',
    'capitalFlowMixed',
    'capitalFlowOutflow',
    'strategySummaryDividendStable',
    'alertPriceDrop',
    'instFund',
    'dividendImplemented',
    'sourceSinaFinance',
    'separator',
    'currencyPerShare',
  ].forEach((key) => assertIncludes(file, key));
});
