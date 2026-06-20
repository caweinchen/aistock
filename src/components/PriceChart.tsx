import { StyleSheet, Text, View } from 'react-native';
import Svg, { Circle, Line, Polyline, Text as SvgText } from 'react-native-svg';
import type { PricePoint, StockSummary } from '../types';
import { formatPrice } from '../utils/formatters';
import { useTranslation } from '../i18n';

interface PriceChartProps {
  stock?: StockSummary;
  history: PricePoint[];
}

export function PriceChart({ stock, history }: PriceChartProps) {
  const { t } = useTranslation();
  const width = 320;
  const height = 160;
  const paddingX = 18;
  const paddingY = 22;
  
  if (history.length === 0) return null;
  
  const prices = history.map((point) => point.close);
  const min = Math.min(...prices);
  const max = Math.max(...prices);
  const range = max - min || 1;
  const latest = history[history.length - 1];
  const first = history[0];
  const trend = latest.close - first.close;
  const isPositive = trend >= 0;

  const points = history
    .map((point, index) => {
      const x = paddingX + (index / Math.max(1, history.length - 1)) * (width - paddingX * 2);
      const y = paddingY + ((max - point.close) / range) * (height - paddingY * 2);
      return `${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(' ');

  const lastX = paddingX + (width - paddingX * 2);
  const lastY = paddingY + ((max - latest.close) / range) * (height - paddingY * 2);
  const lineColor = isPositive ? '#0F8B8D' : '#DC2626';

  return (
    <View style={styles.chartPanel}>
      <View style={styles.chartHeader}>
        <View>
          <Text style={styles.chartTitle}>{t.chart.title}</Text>
          <Text style={styles.subtleText}>{stock ? `${stock.name} · ${t.chart.last} ${history.length} ${t.chart.days}` : `${t.chart.last} 9 ${t.chart.days}`}</Text>
        </View>
        <View style={styles.chartValueBlock}>
          <Text style={styles.chartPrice}>{formatPrice(latest.close)}</Text>
          <Text style={[styles.chartTrend, { color: lineColor }]}>
            {isPositive ? '+' : ''}
            {trend.toFixed(2)}
          </Text>
        </View>
      </View>
      <Svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`}>
        <Line x1={paddingX} x2={width - paddingX} y1={paddingY} y2={paddingY} stroke="#E5E7EB" />
        <Line x1={paddingX} x2={width - paddingX} y1={height / 2} y2={height / 2} stroke="#EEF2F7" />
        <Line x1={paddingX} x2={width - paddingX} y1={height - paddingY} y2={height - paddingY} stroke="#E5E7EB" />
        <Polyline points={points} fill="none" stroke={lineColor} strokeWidth={3} strokeLinejoin="round" />
        <Circle cx={lastX} cy={lastY} r={4.5} fill="#FFFFFF" stroke={lineColor} strokeWidth={3} />
        <SvgText x={paddingX} y={height - 4} fill="#6B7280" fontSize="11">
          {first.date}
        </SvgText>
        <SvgText x={width - paddingX - 34} y={height - 4} fill="#6B7280" fontSize="11">
          {latest.date}
        </SvgText>
        <SvgText x={paddingX} y={16} fill="#6B7280" fontSize="11">
          {formatPrice(max)}
        </SvgText>
        <SvgText x={paddingX} y={height - paddingY + 15} fill="#6B7280" fontSize="11">
          {formatPrice(min)}
        </SvgText>
      </Svg>
    </View>
  );
}

const styles = StyleSheet.create({
  chartPanel: {
    backgroundColor: '#FFFFFF',
    borderColor: '#D8DEE9',
    borderRadius: 8,
    borderWidth: 1,
    gap: 12,
    padding: 16,
  },
  chartHeader: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: 12,
  },
  chartTitle: {
    color: '#162033',
    fontSize: 18,
    fontWeight: '800',
  },
  subtleText: {
    color: '#6B7280',
    fontSize: 13,
  },
  chartValueBlock: {
    alignItems: 'flex-end',
    gap: 3,
  },
  chartPrice: {
    color: '#162033',
    fontSize: 18,
    fontWeight: '800',
  },
  chartTrend: {
    fontSize: 13,
    fontWeight: '800',
  },
});