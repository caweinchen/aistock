import { ActivityIndicator, Pressable, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { Minus, Plus, TrendingDown, TrendingUp } from 'lucide-react-native';
import type { StockSummary } from '../types';
import { formatPrice, formatPercent, getScoreColor } from '../utils/formatters';
import { useTranslateSignal, useTranslation } from '../i18n';

interface StockRowProps {
  stock: StockSummary;
  isSelected: boolean;
  isInWatchlist: boolean;
  isUpdatingWatchlist: boolean;
  onPress: () => void;
  onToggleWatchlist: () => void;
}

export function StockRow({
  stock,
  isSelected,
  isInWatchlist,
  isUpdatingWatchlist,
  onPress,
  onToggleWatchlist,
}: StockRowProps) {
  const isPositive = stock.change_percent >= 0;
  const scoreColor = getScoreColor(stock.score);
  const { t } = useTranslation();
  const translatedSignal = useTranslateSignal(stock.signal);

  return (
    <View style={[styles.stockRow, isSelected && styles.stockRowSelected]}>
      <TouchableOpacity accessibilityRole="button" activeOpacity={0.78} style={styles.stockPressArea} onPress={onPress}>
        <View style={styles.stockIdentity}>
          <Text style={styles.stockName}>{stock.name}</Text>
          <Text style={styles.stockCode}>{stock.code}</Text>
        </View>
        <View style={styles.stockPriceBlock}>
          <Text style={styles.stockPrice}>{formatPrice(stock.price)}</Text>
          <View style={styles.changeLine}>
            {isPositive ? <TrendingUp size={14} color="#0F8B8D" /> : <TrendingDown size={14} color="#DC2626" />}
            <Text style={[styles.stockChange, { color: isPositive ? '#0F8B8D' : '#DC2626' }]}>
              {formatPercent(stock.change_percent)}
            </Text>
          </View>
        </View>
        <View style={[styles.scorePill, { borderColor: scoreColor }]}>
          <Text style={[styles.scoreText, { color: scoreColor }]}>{stock.score}</Text>
          <Text style={styles.signalText}>{translatedSignal}</Text>
        </View>
      </TouchableOpacity>
      <View style={styles.watchlistActionWrap}>
        <Pressable
          accessibilityLabel={isInWatchlist ? t.stock.removeWatchlist : t.stock.addWatchlist}
          style={[styles.watchlistAction, isInWatchlist ? styles.watchlistActionRemove : styles.watchlistActionAdd]}
          onPress={onToggleWatchlist}
        >
          {isUpdatingWatchlist ? (
            <ActivityIndicator size="small" color={isInWatchlist ? '#DC2626' : '#0F8B8D'} />
          ) : isInWatchlist ? (
            <Minus size={16} color="#DC2626" />
          ) : (
            <Plus size={16} color="#0F8B8D" />
          )}
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  stockRow: {
    alignItems: 'center',
    borderBottomColor: '#EEF2F7',
    borderBottomWidth: 1,
    flexDirection: 'row',
    minHeight: 82,
    paddingLeft: 14,
    paddingRight: 10,
  },
  stockPressArea: {
    alignItems: 'center',
    flex: 1,
    flexDirection: 'row',
    minHeight: 82,
  },
  stockRowSelected: {
    backgroundColor: '#E9FBF7',
  },
  stockIdentity: {
    flex: 1,
    gap: 4,
    minWidth: 0,
  },
  stockName: {
    color: '#162033',
    fontSize: 16,
    fontWeight: '800',
  },
  stockCode: {
    color: '#6B7280',
    fontSize: 12,
  },
  stockPriceBlock: {
    alignItems: 'flex-end',
    flex: 1,
    gap: 4,
    minWidth: 0,
  },
  stockPrice: {
    color: '#162033',
    fontSize: 16,
    fontWeight: '700',
  },
  changeLine: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: 3,
  },
  stockChange: {
    fontSize: 12,
    fontWeight: '700',
  },
  scorePill: {
    alignItems: 'center',
    borderRadius: 8,
    borderWidth: 1,
    gap: 1,
    height: 48,
    justifyContent: 'center',
    marginLeft: 12,
    width: 58,
  },
  scoreText: {
    fontSize: 16,
    fontWeight: '800',
  },
  signalText: {
    color: '#6B7280',
    fontSize: 11,
  },
  watchlistActionWrap: {
    alignItems: 'flex-end',
    justifyContent: 'center',
    marginLeft: 8,
  },
  watchlistAction: {
    alignItems: 'center',
    borderRadius: 8,
    borderWidth: 1,
    height: 34,
    justifyContent: 'center',
    width: 34,
  },
  watchlistActionAdd: {
    backgroundColor: '#ECFDF3',
    borderColor: '#A7F3D0',
  },
  watchlistActionRemove: {
    backgroundColor: '#FEF2F2',
    borderColor: '#FECACA',
  },
});