import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { ArrowLeft, Check, RefreshCcw, Server, Wifi, WifiOff } from 'lucide-react-native';
import { useState, useEffect } from 'react';
import { useTranslation } from '../i18n';
import { getServerConfig, setServerConfig, type ServerConfig } from '../services/storage';
import { clearCache } from '../services/api';

interface SettingsScreenProps {
  onBack?: () => void;
  onConfigSaved?: () => void;
}

export function SettingsScreen({ onBack, onConfigSaved }: SettingsScreenProps) {
  const { t } = useTranslation();
  const [host, setHost] = useState('127.0.0.1');
  const [port, setPort] = useState('8000');
  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState<'success' | 'failed' | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);

  useEffect(() => {
    const config = getServerConfig();
    setHost(config.host);
    setPort(String(config.port));
  }, []);

  const handleTestConnection = async () => {
    setIsTesting(true);
    setTestResult(null);
    try {
      const response = await fetch(`http://${host}:${port}/api/stocks`, {
        method: 'GET',
      });
      setTestResult(response.ok ? 'success' : 'failed');
    } catch {
      setTestResult('failed');
    } finally {
      setIsTesting(false);
    }
  };

  const handleSave = () => {
    setIsSaving(true);
    const newConfig: ServerConfig = {
      host: host.trim() || '127.0.0.1',
      port: parseInt(port, 10) || 8000,
    };
    setServerConfig(newConfig);
    clearCache();

    setTimeout(() => {
      setIsSaving(false);
      setShowSuccess(true);

      // 1.5秒后自动返回首页并刷新数据
      setTimeout(() => {
        if (onConfigSaved) {
          onConfigSaved();
        }
        if (onBack) {
          onBack();
        }
      }, 1500);
    }, 500);
  };

  const handleReset = () => {
    setHost('127.0.0.1');
    setPort('8000');
    setTestResult(null);
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <View style={styles.header}>
        <Pressable style={styles.backButton} onPress={onBack}>
          <ArrowLeft size={20} color="#162033" />
        </Pressable>
        <Text style={styles.title}>{t.settings.title}</Text>
        <View style={styles.placeholder} />
      </View>

      <View style={styles.section}>
        <View style={styles.sectionHeader}>
          <Server size={20} color="#0F8B8D" />
          <Text style={styles.sectionTitle}>{t.settings.serverConfig}</Text>
        </View>

        <View style={styles.configCard}>
          <View style={styles.inputGroup}>
            <Text style={styles.inputLabel}>{t.settings.host}</Text>
            <TextInput
              style={styles.input}
              value={host}
              onChangeText={setHost}
              placeholder={t.settings.defaultHost}
              placeholderTextColor="#9CA3AF"
              autoCapitalize="none"
              autoCorrect={false}
              keyboardType="url"
            />
          </View>

          <View style={styles.inputGroup}>
            <Text style={styles.inputLabel}>{t.settings.port}</Text>
            <TextInput
              style={styles.input}
              value={port}
              onChangeText={setPort}
              placeholder={t.settings.defaultPort}
              placeholderTextColor="#9CA3AF"
              keyboardType="number-pad"
            />
          </View>

          <View style={styles.currentConfig}>
            <Text style={styles.currentConfigLabel}>{t.settings.currentConfig}:</Text>
            <Text style={styles.currentConfigValue}>http://{host}:{port}</Text>
          </View>
        </View>
      </View>

      <View style={styles.actions}>
        <Pressable
          style={[styles.actionButton, styles.testButton]}
          onPress={handleTestConnection}
          disabled={isTesting}
        >
          {isTesting ? (
            <ActivityIndicator size="small" color="#0F8B8D" />
          ) : testResult === 'success' ? (
            <Wifi size={18} color="#0F8B8D" />
          ) : testResult === 'failed' ? (
            <WifiOff size={18} color="#DC2626" />
          ) : (
            <Wifi size={18} color="#0F8B8D" />
          )}
          <Text style={[
            styles.actionButtonText,
            testResult === 'failed' && styles.failedText,
          ]}>
            {testResult === 'success'
              ? t.settings.connectionSuccess
              : testResult === 'failed'
                ? t.settings.connectionFailed
                : t.settings.testConnection}
          </Text>
        </Pressable>

        <Pressable
          style={[styles.actionButton, styles.resetButton]}
          onPress={handleReset}
        >
          <RefreshCcw size={18} color="#6B7280" />
          <Text style={styles.resetButtonText}>{t.settings.reset}</Text>
        </Pressable>

        <Pressable
          style={[styles.actionButton, styles.saveButton]}
          onPress={handleSave}
          disabled={isSaving || showSuccess}
        >
          {isSaving ? (
            <ActivityIndicator size="small" color="#FFFFFF" />
          ) : showSuccess ? (
            <Check size={18} color="#FFFFFF" />
          ) : (
            <Check size={18} color="#FFFFFF" />
          )}
          <Text style={styles.saveButtonText}>
            {showSuccess ? t.settings.saved : t.settings.save}
          </Text>
        </Pressable>

        {showSuccess && (
          <View style={styles.successBanner}>
            <Text style={styles.successText}>{t.settings.restartRequired}</Text>
          </View>
        )}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F6F7FB',
  },
  content: {
    padding: 20,
    gap: 20,
  },
  header: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
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
  title: {
    color: '#162033',
    fontSize: 20,
    fontWeight: '800',
  },
  placeholder: {
    width: 42,
  },
  section: {
    gap: 12,
  },
  sectionHeader: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: 8,
  },
  sectionTitle: {
    color: '#162033',
    fontSize: 16,
    fontWeight: '700',
  },
  configCard: {
    backgroundColor: '#FFFFFF',
    borderColor: '#E5E7EB',
    borderRadius: 12,
    borderWidth: 1,
    gap: 16,
    padding: 16,
  },
  inputGroup: {
    gap: 6,
  },
  inputLabel: {
    color: '#4B5563',
    fontSize: 13,
    fontWeight: '600',
  },
  input: {
    backgroundColor: '#F8FAFC',
    borderColor: '#E5E7EB',
    borderRadius: 8,
    borderWidth: 1,
    color: '#162033',
    fontSize: 15,
    minHeight: 44,
    paddingHorizontal: 12,
  },
  currentConfig: {
    backgroundColor: '#F0FDF4',
    borderRadius: 8,
    padding: 12,
  },
  currentConfigLabel: {
    color: '#6B7280',
    fontSize: 12,
  },
  currentConfigValue: {
    color: '#0F766E',
    fontSize: 14,
    fontWeight: '600',
    marginTop: 2,
  },
  actions: {
    gap: 12,
  },
  actionButton: {
    alignItems: 'center',
    borderRadius: 8,
    flexDirection: 'row',
    gap: 8,
    justifyContent: 'center',
    minHeight: 48,
    paddingHorizontal: 16,
  },
  testButton: {
    backgroundColor: '#FFFFFF',
    borderColor: '#0F8B8D',
    borderWidth: 1,
  },
  actionButtonText: {
    color: '#0F8B8D',
    fontSize: 14,
    fontWeight: '600',
  },
  failedText: {
    color: '#DC2626',
  },
  resetButton: {
    backgroundColor: '#FFFFFF',
    borderColor: '#E5E7EB',
    borderWidth: 1,
  },
  resetButtonText: {
    color: '#6B7280',
    fontSize: 14,
    fontWeight: '600',
  },
  saveButton: {
    backgroundColor: '#0F8B8D',
  },
  saveButtonText: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '700',
  },
  successBanner: {
    backgroundColor: '#ECFDF5',
    borderColor: '#A7F3D0',
    borderRadius: 8,
    borderWidth: 1,
    padding: 14,
    alignItems: 'center',
  },
  successText: {
    color: '#047857',
    fontSize: 14,
    fontWeight: '600',
    textAlign: 'center',
  },
});
