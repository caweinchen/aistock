import { StyleSheet, Text, View } from 'react-native';
import { AlertTriangle } from 'lucide-react-native';
import type { AlertItem } from '../types';
import { useTranslateAlert } from '../i18n';

interface AlertCardProps {
  alert: AlertItem;
}

export function AlertCard({ alert }: AlertCardProps) {
  const tone = alert.level === 'low' ? '#0F8B8D' : alert.level === 'medium' ? '#B45309' : '#B42318';
  const translateAlert = useTranslateAlert();

  return (
    <View style={[styles.warningPanel, { borderColor: `${tone}55` }]}>
      <View style={[styles.warningIcon, { backgroundColor: `${tone}1A` }]}>
        <AlertTriangle size={20} color={tone} />
      </View>
      <View style={styles.warningCopy}>
        <Text style={[styles.warningTitle, { color: tone }]}>{translateAlert.title(alert.title)}</Text>
        <Text style={styles.warningText}>{translateAlert.message(alert.message)}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  warningPanel: {
    backgroundColor: '#FFF7ED',
    borderColor: '#FED7AA',
    borderRadius: 8,
    borderWidth: 1,
    flexDirection: 'row',
    gap: 12,
    padding: 14,
  },
  warningIcon: {
    alignItems: 'center',
    backgroundColor: '#FFEDD5',
    borderRadius: 8,
    height: 38,
    justifyContent: 'center',
    width: 38,
  },
  warningCopy: {
    flex: 1,
    gap: 5,
  },
  warningTitle: {
    color: '#92400E',
    fontSize: 14,
    fontWeight: '800',
  },
  warningText: {
    color: '#9A3412',
    fontSize: 13,
    lineHeight: 20,
  },
});
