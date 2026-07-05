import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { ArrowLeft } from 'lucide-react-native';
import { useTranslation } from '../i18n';

interface LegalScreenProps {
  type: 'terms' | 'privacy';
  onBack?: () => void;
}

export function LegalScreen({ type, onBack }: LegalScreenProps) {
  const { t } = useTranslation();
  const title = type === 'terms' ? t.legal.termsTitle : t.legal.privacyTitle;
  const content = type === 'terms' ? t.legal.termsContent : t.legal.privacyContent;

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <View style={styles.header}>
        <Pressable style={styles.backButton} onPress={onBack}>
          <ArrowLeft size={20} color="#162033" />
        </Pressable>
        <Text style={styles.title}>{title}</Text>
        <View style={styles.placeholder} />
      </View>

      <View style={styles.body}>
        <Text style={styles.sectionTitle}>{title}</Text>
        <Text style={styles.sectionContent}>{content}</Text>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F6F7FB' },
  content: { padding: 20, gap: 16 },
  header: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between' },
  backButton: {
    alignItems: 'center',
    backgroundColor: '#FFFFFF',
    borderColor: '#E5E7EB',
    borderRadius: 8,
    borderWidth: 1,
    height: 42,
    justifyContent: 'center',
    width: 42,
  },
  title: { color: '#162033', fontSize: 20, fontWeight: '800' },
  placeholder: { width: 42 },
  body: { backgroundColor: '#FFFFFF', borderColor: '#E5E7EB', borderRadius: 12, borderWidth: 1, padding: 16 },
  sectionTitle: { color: '#162033', fontSize: 18, fontWeight: '700', marginBottom: 12 },
  sectionContent: { color: '#374151', fontSize: 14, lineHeight: 22 },
});
