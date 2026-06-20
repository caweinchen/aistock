import { ActivityIndicator, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';
import type { StrategyTemplate } from '../types';
import { useTranslation } from '../i18n';

interface BacktestBuilderProps {
  name: string;
  template: StrategyTemplate;
  lookbackDays: number;
  isCreating: boolean;
  onChangeName: (value: string) => void;
  onChangeTemplate: (value: StrategyTemplate) => void;
  onChangeLookbackDays: (value: number) => void;
  onCreate: () => void;
}

export function BacktestBuilder({
  name,
  template,
  lookbackDays,
  isCreating,
  onChangeName,
  onChangeTemplate,
  onChangeLookbackDays,
  onCreate,
}: BacktestBuilderProps) {
  const { t, locale } = useTranslation();

  return (
    <View style={styles.builderPanel}>
      <Text style={styles.builderTitle}>{t.backtest.title}</Text>
      <TextInput
        style={styles.builderInput}
        value={name}
        onChangeText={onChangeName}
        placeholder={t.backtest.name}
        placeholderTextColor="#9CA3AF"
      />
      <View style={styles.optionGroup}>
        <Text style={styles.optionLabel}>{t.backtest.template}</Text>
        <View style={styles.optionRow}>
          <OptionButton
            isSelected={template === 'trend-breakout'}
            label={t.backtest.trendBreakout}
            onPress={() => onChangeTemplate('trend-breakout')}
          />
          <OptionButton
            isSelected={template === 'low-valuation-reversal'}
            label={t.backtest.lowValuationReversal}
            onPress={() => onChangeTemplate('low-valuation-reversal')}
          />
          <OptionButton
            isSelected={template === 'dividend-defense'}
            label={t.backtest.dividendDefense}
            onPress={() => onChangeTemplate('dividend-defense')}
          />
        </View>
      </View>
      <View style={styles.optionGroup}>
        <Text style={styles.optionLabel}>{t.backtest.lookbackDays}</Text>
        <View style={styles.optionRow}>
          {[90, 180, 365].map((days) => (
            <OptionButton
              key={days}
              isSelected={lookbackDays === days}
              label={`${days} ${t.backtest.days}`}
              onPress={() => onChangeLookbackDays(days)}
            />
          ))}
        </View>
      </View>
      <Pressable style={styles.createBacktestButton} onPress={onCreate}>
        {isCreating ? <ActivityIndicator size="small" color="#FFFFFF" /> : null}
        <Text style={styles.createBacktestText}>{isCreating ? t.backtest.running : t.backtest.run}</Text>
      </Pressable>
    </View>
  );
}

function OptionButton({ label, isSelected, onPress }: { label: string; isSelected: boolean; onPress: () => void }) {
  return (
    <Pressable style={[styles.optionButton, isSelected && styles.optionButtonSelected]} onPress={onPress}>
      <Text style={[styles.optionButtonText, isSelected && styles.optionButtonTextSelected]}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  builderPanel: {
    backgroundColor: '#FFFFFF',
    borderColor: '#D8DEE9',
    borderRadius: 8,
    borderWidth: 1,
    gap: 14,
    padding: 16,
  },
  builderTitle: {
    color: '#162033',
    fontSize: 17,
    fontWeight: '800',
  },
  builderInput: {
    backgroundColor: '#F8FAFC',
    borderColor: '#E5E7EB',
    borderRadius: 8,
    borderWidth: 1,
    color: '#162033',
    fontSize: 15,
    minHeight: 44,
    paddingHorizontal: 12,
  },
  optionGroup: {
    gap: 8,
  },
  optionLabel: {
    color: '#4B5563',
    fontSize: 13,
    fontWeight: '800',
  },
  optionRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  optionButton: {
    alignItems: 'center',
    backgroundColor: '#F8FAFC',
    borderColor: '#E5E7EB',
    borderRadius: 8,
    borderWidth: 1,
    minHeight: 36,
    paddingHorizontal: 11,
    justifyContent: 'center',
  },
  optionButtonSelected: {
    backgroundColor: '#E9FBF7',
    borderColor: '#0F8B8D',
  },
  optionButtonText: {
    color: '#4B5563',
    fontSize: 13,
    fontWeight: '700',
  },
  optionButtonTextSelected: {
    color: '#0F766E',
  },
  createBacktestButton: {
    alignItems: 'center',
    backgroundColor: '#0F8B8D',
    borderRadius: 8,
    flexDirection: 'row',
    gap: 8,
    justifyContent: 'center',
    minHeight: 42,
  },
  createBacktestText: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '800',
  },
});