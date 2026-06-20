import { StyleSheet, Text, View } from 'react-native';
import { PieChart } from 'lucide-react-native';
import type { FactorScore } from '../types';

const factorColors: Record<string, string> = {
  capital_flow: '#0F8B8D',
  valuation: '#7C3AED',
  momentum: '#D97706',
  volatility: '#DC2626',
};

interface FactorTileProps {
  factor: FactorScore;
}

export function FactorTile({ factor }: FactorTileProps) {
  const tone = factorColors[factor.key] ?? '#0F8B8D';

  return (
    <View style={styles.factorTile}>
      <View style={[styles.factorIcon, { backgroundColor: `${tone}1A` }]}>
        <PieChart size={18} color={tone} />
      </View>
      <Text style={styles.factorValue}>{factor.value}</Text>
      <Text style={styles.factorLabel}>{factor.label}</Text>
      <Text style={styles.factorDescription}>{factor.description}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  factorTile: {
    alignItems: 'center',
    backgroundColor: '#FFFFFF',
    borderColor: '#E5E7EB',
    borderRadius: 8,
    borderWidth: 1,
    flexBasis: '47%',
    flexGrow: 1,
    gap: 6,
    minHeight: 150,
    padding: 14,
  },
  factorIcon: {
    alignItems: 'center',
    borderRadius: 8,
    height: 38,
    justifyContent: 'center',
    width: 38,
  },
  factorValue: {
    color: '#162033',
    fontSize: 26,
    fontWeight: '800',
  },
  factorLabel: {
    color: '#6B7280',
    fontSize: 13,
  },
  factorDescription: {
    color: '#4B5563',
    fontSize: 12,
    lineHeight: 18,
    textAlign: 'center',
  },
});