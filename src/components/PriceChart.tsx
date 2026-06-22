import { useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import Svg, { Circle, Line, Polyline, Rect, Text as SvgText } from 'react-native-svg';
import type { PricePoint, StockSummary } from '../types';
import { formatPrice } from '../utils/formatters';
import { useTranslation } from '../i18n';

interface PriceChartProps {
  stock?: StockSummary;
  history: PricePoint[];
}

interface HoverData {
  index: number;
  x: number;
  y: number;
  date: string;
  price: number;
}

export function PriceChart({ stock, history }: PriceChartProps) {
  const { t } = useTranslation();
  const width = 320;
  const height = 140;
  const paddingX = 18;
  const paddingY = 20;
  const [hoverData, setHoverData] = useState<HoverData | null>(null);
  
  if (history.length === 0) return null;
  
  const prices = history.map((point) => point.close);
  const min = Math.min(...prices);
  const max = Math.max(...prices);
  const range = max - min || 1;
  const latest = history[history.length - 1];
  const first = history[0];
  const trend = latest.close - first.close;
  const isPositive = trend >= 0;

  // 计算每个数据点的坐标
  const dataPoints = history.map((point, index) => {
    const x = paddingX + (index / Math.max(1, history.length - 1)) * (width - paddingX * 2);
    const y = paddingY + ((max - point.close) / range) * (height - paddingY * 2);
    return { x, y, point, index };
  });

  const points = dataPoints
    .map((p) => `${p.x.toFixed(2)},${p.y.toFixed(2)}`)
    .join(' ');

  const lastX = paddingX + (width - paddingX * 2);
  const lastY = paddingY + ((max - latest.close) / range) * (height - paddingY * 2);
  const lineColor = isPositive ? '#0F8B8D' : '#DC2626';

  // 处理鼠标/触摸移动
  const handlePointerMove = (event: any) => {
    const { locationX } = event.nativeEvent;
    // 计算鼠标位置对应的数据索引
    const chartWidth = width - paddingX * 2;
    const relativeX = locationX - paddingX;
    
    if (relativeX < 0 || relativeX > chartWidth) {
      setHoverData(null);
      return;
    }
    
    const ratio = relativeX / chartWidth;
    const index = Math.round(ratio * (history.length - 1));
    
    if (index >= 0 && index < history.length) {
      const point = history[index];
      const x = paddingX + (index / Math.max(1, history.length - 1)) * chartWidth;
      const y = paddingY + ((max - point.close) / range) * (height - paddingY * 2);
      
      setHoverData({
        index,
        x,
        y,
        date: point.date,
        price: point.close,
      });
    }
  };

  const handlePointerLeave = () => {
    setHoverData(null);
  };

  // 计算 tooltip 位置
  const tooltipWidth = 100;
  const tooltipHeight = 50;
  const tooltipX = hoverData ? Math.min(Math.max(hoverData.x - tooltipWidth / 2, paddingX), width - paddingX - tooltipWidth) : 0;
  const tooltipY = hoverData ? Math.max(hoverData.y - tooltipHeight - 10, 5) : 0;

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
      <View 
        style={styles.chartContainer}
        onPointerMove={handlePointerMove}
        onPointerLeave={handlePointerLeave}
      >
        <Svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`}>
          {/* 背景网格线 */}
          <Line x1={paddingX} x2={width - paddingX} y1={paddingY} y2={paddingY} stroke="#E5E7EB" />
          <Line x1={paddingX} x2={width - paddingX} y1={height / 2} y2={height / 2} stroke="#EEF2F7" />
          <Line x1={paddingX} x2={width - paddingX} y1={height - paddingY} y2={height - paddingY} stroke="#E5E7EB" />
          
          {/* 价格曲线 */}
          <Polyline points={points} fill="none" stroke={lineColor} strokeWidth={3} strokeLinejoin="round" />
          
          {/* 最新价格点 */}
          <Circle cx={lastX} cy={lastY} r={4.5} fill="#FFFFFF" stroke={lineColor} strokeWidth={3} />
          
          {/* 最高最低价格标签 */}
          <SvgText x={paddingX} y={12} fill="#6B7280" fontSize="11">
            {formatPrice(max)}
          </SvgText>
          <SvgText x={paddingX} y={height - paddingY + 12} fill="#6B7280" fontSize="11">
            {formatPrice(min)}
          </SvgText>
          
          {/* 悬停时的指示线和点 */}
          {hoverData && (
            <>
              {/* 垂直指示线 */}
              <Line 
                x1={hoverData.x} 
                x2={hoverData.x} 
                y1={paddingY} 
                y2={height - paddingY} 
                stroke="#162033" 
                strokeWidth={1} 
                strokeOpacity={0.3}
              />
              {/* 悬停点 */}
              <Circle 
                cx={hoverData.x} 
                cy={hoverData.y} 
                r={6} 
                fill="#FFFFFF" 
                stroke={lineColor} 
                strokeWidth={3} 
              />
              {/* Tooltip 背景 */}
              <Rect 
                x={tooltipX} 
                y={tooltipY} 
                width={tooltipWidth} 
                height={tooltipHeight} 
                rx={6} 
                fill="#162033" 
                fillOpacity={0.9}
              />
              {/* Tooltip 日期 */}
              <SvgText 
                x={tooltipX + tooltipWidth / 2} 
                y={tooltipY + 18} 
                fill="#FFFFFF" 
                fontSize="11" 
                textAnchor="middle"
              >
                {hoverData.date}
              </SvgText>
              {/* Tooltip 价格 */}
              <SvgText 
                x={tooltipX + tooltipWidth / 2} 
                y={tooltipY + 36} 
                fill={lineColor} 
                fontSize="14" 
                fontWeight="bold"
                textAnchor="middle"
              >
                {formatPrice(hoverData.price)}
              </SvgText>
            </>
          )}
        </Svg>
      </View>
      <View style={styles.dateRow}>
        <Text style={styles.dateText}>{first.date}</Text>
        <Text style={styles.dateText}>{latest.date}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  chartPanel: {
    backgroundColor: '#FFFFFF',
    borderColor: '#D8DEE9',
    borderRadius: 8,
    borderWidth: 1,
    gap: 8,
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
  chartContainer: {
    cursor: 'crosshair',
  },
  dateRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingHorizontal: 18,
  },
  dateText: {
    color: '#6B7280',
    fontSize: 12,
  },
});