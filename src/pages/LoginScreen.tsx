import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { Globe, Lock, Mail, Server, ShieldCheck } from 'lucide-react-native';
import { useState, useEffect } from 'react';
import { useAuth } from '../hooks/useAuth';
import { useTranslation } from '../i18n';
import type { Locale } from '../i18n/types';

interface LoginScreenProps {
  onSuccess?: () => void;
  onOpenSettings?: () => void;
}

export function LoginScreen({ onSuccess, onOpenSettings }: LoginScreenProps) {
  const { t, locale, setLocale } = useTranslation();
  const { isLoggedIn, isLoading, error, login } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  useEffect(() => {
    if (isLoggedIn && onSuccess) {
      onSuccess();
    }
  }, [isLoggedIn, onSuccess]);

  const cycleLanguage = () => {
    const locales: Locale[] = ['zh', 'zh-Hant', 'en'];
    const currentIndex = locales.indexOf(locale);
    const nextIndex = (currentIndex + 1) % locales.length;
    setLocale(locales[nextIndex]);
  };

  const getLanguageLabel = () => {
    switch (locale) {
      case 'zh': return '中';
      case 'zh-Hant': return '繁';
      case 'en': return 'EN';
      default: return '中';
    }
  };

  const handleLogin = async () => {
    if (!username.trim() || !password.trim()) return;
    const success = await login(username, password);
    if (success && onSuccess) {
      onSuccess();
    }
  };

  if (isLoggedIn) {
    return null;
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <View style={styles.header}>
        <View style={styles.placeholder} />
        <Text style={styles.title}>{t.login.title}</Text>
        <View style={styles.headerButtons}>
          <Pressable style={styles.langButton} onPress={cycleLanguage}>
            <Globe size={16} color="#0F8B8D" />
            <Text style={styles.langText}>{getLanguageLabel()}</Text>
          </Pressable>
          <Pressable style={styles.settingsButton} onPress={onOpenSettings}>
            <Server size={20} color="#0F8B8D" />
          </Pressable>
        </View>
      </View>

      <View style={styles.loginCard}>
        <View style={styles.logo}>
          <ShieldCheck size={48} color="#0F8B8D" />
        </View>
        <Text style={styles.welcomeText}>{t.login.welcome}</Text>
        <Text style={styles.subtitle}>{t.login.subtitle}</Text>

        <View style={styles.form}>
          <View style={styles.inputGroup}>
            <Mail size={18} color="#6B7280" />
            <TextInput
              style={styles.input}
              value={username}
              onChangeText={setUsername}
              placeholder={t.login.username}
              placeholderTextColor="#9CA3AF"
              keyboardType="email-address"
              autoCapitalize="none"
              onSubmitEditing={handleLogin}
            />
          </View>

          <View style={styles.inputGroup}>
            <Lock size={18} color="#6B7280" />
            <TextInput
              style={styles.input}
              value={password}
              onChangeText={setPassword}
              placeholder={t.login.password}
              placeholderTextColor="#9CA3AF"
              secureTextEntry={!showPassword}
              onSubmitEditing={handleLogin}
            />
            <Pressable onPress={() => setShowPassword(!showPassword)}>
              <Text style={styles.toggleText}>{showPassword ? t.login.hide : t.login.show}</Text>
            </Pressable>
          </View>

          {error && (
            <View style={styles.errorMessage}>
              <Text style={styles.errorText}>{error}</Text>
            </View>
          )}

          <Pressable style={styles.loginButton} onPress={handleLogin} disabled={isLoading}>
            {isLoading ? <ActivityIndicator size="small" color="#FFFFFF" /> : null}
            <Text style={styles.loginButtonText}>{isLoading ? t.login.loggingIn : t.login.login}</Text>
          </Pressable>

          <Pressable style={styles.forgotButton}>
            <Text style={styles.forgotText}>{t.login.forgotPassword}</Text>
          </Pressable>
        </View>
      </View>

      <View style={styles.registerSection}>
        <Text style={styles.registerText}>{t.login.noAccount}</Text>
        <Pressable>
          <Text style={styles.registerLink}>{t.login.signUp}</Text>
        </Pressable>
      </View>

      <View style={styles.disclaimer}>
        <Text style={styles.disclaimerText}>
          {t.login.agree}
        </Text>
        <Pressable>
          <Text style={styles.disclaimerLink}>{t.login.terms}</Text>
        </Pressable>
        <Text style={styles.disclaimerText}>{t.login.and}</Text>
        <Pressable>
          <Text style={styles.disclaimerLink}>{t.login.privacy}</Text>
        </Pressable>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F6F7FB' },
  content: { padding: 20, gap: 16 },
  header: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between' },
  headerButtons: { flexDirection: 'row', gap: 8 },
  langButton: {
    alignItems: 'center',
    backgroundColor: '#E9FBF7',
    borderColor: '#0F8B8D',
    borderRadius: 8,
    borderWidth: 1,
    flexDirection: 'row',
    gap: 4,
    height: 42,
    justifyContent: 'center',
    paddingHorizontal: 12,
  },
  langText: { color: '#0F8B8D', fontSize: 13, fontWeight: '700' },
  settingsButton: {
    alignItems: 'center',
    backgroundColor: '#E9FBF7',
    borderColor: '#0F8B8D',
    borderRadius: 8,
    borderWidth: 1,
    height: 42,
    justifyContent: 'center',
    width: 42,
  },
  title: { color: '#162033', fontSize: 20, fontWeight: '800' },
  placeholder: { width: 42 },
  loginCard: {
    backgroundColor: '#FFFFFF',
    borderColor: '#E5E7EB',
    borderRadius: 16,
    borderWidth: 1,
    gap: 16,
    padding: 24,
  },
  logo: {
    alignItems: 'center',
    backgroundColor: '#E9FBF7',
    borderRadius: 16,
    height: 80,
    justifyContent: 'center',
    width: 80,
  },
  welcomeText: { color: '#162033', fontSize: 24, fontWeight: '800', textAlign: 'center' },
  subtitle: { color: '#6B7280', fontSize: 14, textAlign: 'center' },
  form: { gap: 16 },
  inputGroup: {
    alignItems: 'center',
    backgroundColor: '#F8FAFC',
    borderColor: '#E5E7EB',
    borderRadius: 8,
    borderWidth: 1,
    flexDirection: 'row',
    gap: 10,
    minHeight: 48,
    paddingHorizontal: 14,
  },
  input: {
    color: '#162033',
    flex: 1,
    fontSize: 15,
  },
  toggleText: { color: '#0F8B8D', fontSize: 13 },
  errorMessage: { padding: 12, backgroundColor: '#FEF3F2', borderRadius: 8 },
  errorText: { color: '#B42318', fontSize: 13 },
  loginButton: {
    alignItems: 'center',
    backgroundColor: '#0F8B8D',
    borderRadius: 8,
    flexDirection: 'row',
    gap: 8,
    justifyContent: 'center',
    minHeight: 48,
  },
  loginButtonText: { color: '#FFFFFF', fontSize: 15, fontWeight: '800' },
  forgotButton: { alignItems: 'center' },
  forgotText: { color: '#0F8B8D', fontSize: 14 },
  registerSection: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: 8,
  },
  registerText: { color: '#6B7280', fontSize: 14 },
  registerLink: { color: '#0F8B8D', fontSize: 14, fontWeight: '700' },
  disclaimer: {
    alignItems: 'center',
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 4,
    marginTop: 24,
    paddingHorizontal: 16,
  },
  disclaimerText: { color: '#9CA3AF', fontSize: 12 },
  disclaimerLink: { color: '#0F8B8D', fontSize: 12, fontWeight: '700' },
});