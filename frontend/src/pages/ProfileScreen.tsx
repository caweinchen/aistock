import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { ArrowLeft, Check, Globe, Key, RefreshCcw, Shield, User } from 'lucide-react-native';
import { useState, useEffect } from 'react';
import { useTranslation } from '../i18n';
import { getStoredUser, getApiBaseUrl, getAuthToken } from '../services/storage';
import type { Locale } from '../i18n/types';

interface ProfileScreenProps {
  onBack?: () => void;
  onLogout?: () => void;
  onOpenTerms?: () => void;
  onOpenPrivacy?: () => void;
}

export function ProfileScreen({ onBack, onLogout, onOpenTerms, onOpenPrivacy }: ProfileScreenProps) {
  const { t, locale, setLocale } = useTranslation();
  const [username, setUsername] = useState('');
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPasswordSection, setShowPasswordSection] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [passwordScore, setPasswordScore] = useState(0);

  useEffect(() => {
    const user = getStoredUser();
    if (user) {
      setUsername(user);
    }
  }, []);

  const validatePassword = (password: string): number => {
    let score = 0;
    if (password.length >= 8) score++;
    if (/[A-Z]/.test(password)) score++;
    if (/[a-z]/.test(password)) score++;
    if (/[0-9]/.test(password)) score++;
    if (/[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]/.test(password)) score++;
    return score;
  };

  const handlePasswordChange = (password: string) => {
    setNewPassword(password);
    setPasswordScore(validatePassword(password));
  };

  const generatePassword = async () => {
    setIsGenerating(true);
    try {
      const apiBase = getApiBaseUrl();
      const response = await fetch(`${apiBase}/api/auth/generate-password`);
      const data = await response.json();
      setNewPassword(data.password);
      setConfirmPassword(data.password);
      setPasswordScore(5);
    } catch (err) {
      console.error('Failed to generate password:', err);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleChangePassword = async () => {
    setError(null);
    setSuccess(null);

    if (!oldPassword.trim()) {
      setError(t.profile.oldPassword);
      return;
    }

    if (newPassword !== confirmPassword) {
      setError(t.profile.passwordMismatch);
      return;
    }

    if (passwordScore < 5) {
      setError(t.profile.passwordWeak);
      return;
    }

    setIsLoading(true);
    try {
      let encryptedOldPassword = oldPassword;
      let encryptedNewPassword = newPassword;
      
      try {
        const { encryptPassword } = await import('../utils/crypto');
        encryptedOldPassword = await encryptPassword(oldPassword);
        encryptedNewPassword = await encryptPassword(newPassword);
      } catch (e) {
        console.warn('Failed to encrypt password, sending as plain text:', e);
      }

      const apiBase = getApiBaseUrl();
      const response = await fetch(`${apiBase}/api/auth/change-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username,
          old_password: encryptedOldPassword,
          new_password: encryptedNewPassword,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Failed to change password');
      }

      setSuccess(t.profile.passwordChanged);
      setOldPassword('');
      setNewPassword('');
      setConfirmPassword('');
      setPasswordScore(0);
      setShowPasswordSection(false);
    } catch (err: any) {
      setError(err.message || 'Failed to change password');
    } finally {
      setIsLoading(false);
    }
  };

  const handleLanguageChange = (newLocale: Locale) => {
    setLocale(newLocale);
    setSuccess(t.profile.languageChanged);
    setTimeout(() => setSuccess(null), 2000);
  };

  const getPasswordStrengthColor = () => {
    if (passwordScore <= 2) return '#EF4444';
    if (passwordScore <= 3) return '#F59E0B';
    return '#10B981';
  };

  const getPasswordStrengthLabel = () => {
    if (passwordScore <= 2) return t.profile.passwordWeakLabel;
    if (passwordScore <= 3) return t.profile.passwordMedium;
    return t.profile.passwordStrong;
  };

  const languages: { code: Locale; label: string }[] = [
    { code: 'zh', label: '简体中文' },
    { code: 'zh-Hant', label: '繁體中文' },
    { code: 'en', label: 'English' },
  ];

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <View style={styles.header}>
        <Pressable style={styles.backButton} onPress={onBack}>
          <ArrowLeft size={20} color="#162033" />
        </Pressable>
        <Text style={styles.title}>{t.profile.title}</Text>
        <View style={styles.placeholder} />
      </View>

      {/* 账户信息 */}
      <View style={styles.section}>
        <View style={styles.sectionHeader}>
          <User size={18} color="#0F8B8D" />
          <Text style={styles.sectionTitle}>{t.profile.account}</Text>
        </View>
        <View style={styles.card}>
          <Text style={styles.label}>{t.profile.username}</Text>
          <Text style={styles.value}>{username}</Text>
        </View>
      </View>

      {/* 语言设置 */}
      <View style={styles.section}>
        <View style={styles.sectionHeader}>
          <Globe size={18} color="#0F8B8D" />
          <Text style={styles.sectionTitle}>{t.profile.language}</Text>
        </View>
        <View style={styles.languageOptions}>
          {languages.map((lang) => (
            <Pressable
              key={lang.code}
              style={[
                styles.languageOption,
                locale === lang.code && styles.languageOptionActive,
              ]}
              onPress={() => handleLanguageChange(lang.code)}
            >
              <Text
                style={[
                  styles.languageOptionText,
                  locale === lang.code && styles.languageOptionTextActive,
                ]}
              >
                {lang.label}
              </Text>
              {locale === lang.code && <Check size={16} color="#0F8B8D" />}
            </Pressable>
          ))}
        </View>
      </View>

      <View style={styles.section}>
        <View style={styles.sectionHeader}>
          <Key size={18} color="#0F8B8D" />
          <Text style={styles.sectionTitle}>{t.profile.changePassword}</Text>
        </View>

        {!showPasswordSection ? (
          <Pressable style={styles.changePasswordButton} onPress={() => setShowPasswordSection(true)}>
            <Shield size={18} color="#0F8B8D" />
            <Text style={styles.changePasswordButtonText}>{t.profile.changePassword}</Text>
          </Pressable>
        ) : (
          <View style={styles.passwordForm}>
            <View style={styles.inputGroup}>
              <Text style={styles.inputLabel}>{t.profile.oldPassword}</Text>
              <TextInput
                style={styles.input}
                value={oldPassword}
                onChangeText={setOldPassword}
                placeholder={t.profile.oldPassword}
                placeholderTextColor="#9CA3AF"
                secureTextEntry
              />
            </View>

            <View style={styles.inputGroup}>
              <Text style={styles.inputLabel}>{t.profile.newPassword}</Text>
              <TextInput
                style={styles.input}
                value={newPassword}
                onChangeText={handlePasswordChange}
                placeholder={t.profile.newPassword}
                placeholderTextColor="#9CA3AF"
                secureTextEntry
              />
              {newPassword.length > 0 && (
                <View style={styles.strengthIndicator}>
                  <View style={styles.strengthBar}>
                    {[1, 2, 3, 4, 5].map((i) => (
                      <View
                        key={i}
                        style={[
                          styles.strengthSegment,
                          { backgroundColor: i <= passwordScore ? getPasswordStrengthColor() : '#E5E7EB' },
                        ]}
                      />
                    ))}
                  </View>
                  <Text style={[styles.strengthLabel, { color: getPasswordStrengthColor() }]}>
                    {t.profile.passwordStrength}: {getPasswordStrengthLabel()}
                  </Text>
                </View>
              )}
            </View>

            <View style={styles.inputGroup}>
              <Text style={styles.inputLabel}>{t.profile.confirmPassword}</Text>
              <TextInput
                style={styles.input}
                value={confirmPassword}
                onChangeText={setConfirmPassword}
                placeholder={t.profile.confirmPassword}
                placeholderTextColor="#9CA3AF"
                secureTextEntry
              />
            </View>

            {/* 密码要求 */}
            <View style={styles.requirements}>
              <Text style={styles.requirementsTitle}>{t.profile.passwordRequirements}</Text>
              {[
                { key: 'length', text: t.profile.passwordMinLength, valid: newPassword.length >= 8 },
                { key: 'upper', text: t.profile.passwordUppercase, valid: /[A-Z]/.test(newPassword) },
                { key: 'lower', text: t.profile.passwordLowercase, valid: /[a-z]/.test(newPassword) },
                { key: 'number', text: t.profile.passwordNumber, valid: /[0-9]/.test(newPassword) },
                { key: 'special', text: t.profile.passwordSpecial, valid: /[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]/.test(newPassword) },
              ].map((req) => (
                <View key={req.key} style={styles.requirementItem}>
                  <View style={[styles.checkCircle, req.valid && styles.checkCircleValid]}>
                    {req.valid && <Check size={12} color="#FFFFFF" />}
                  </View>
                  <Text style={[styles.requirementText, req.valid && styles.requirementTextValid]}>
                    {req.text}
                  </Text>
                </View>
              ))}
            </View>

            {/* 生成随机密码 */}
            <Pressable style={styles.generateButton} onPress={generatePassword} disabled={isGenerating}>
              <RefreshCcw size={16} color="#0F8B8D" />
              <Text style={styles.generateButtonText}>
                {isGenerating ? t.common.loading : t.profile.generatePassword}
              </Text>
            </Pressable>

            {error && (
              <View style={styles.errorBanner}>
                <Text style={styles.errorText}>{error}</Text>
              </View>
            )}

            {success && (
              <View style={styles.successBanner}>
                <Text style={styles.successText}>{success}</Text>
              </View>
            )}

            <View style={styles.buttonRow}>
              <Pressable style={styles.cancelButton} onPress={() => {
                setShowPasswordSection(false);
                setOldPassword('');
                setNewPassword('');
                setConfirmPassword('');
                setPasswordScore(0);
                setError(null);
              }}>
                <Text style={styles.cancelButtonText}>{t.profile.cancel}</Text>
              </Pressable>
              <Pressable
                style={[styles.saveButton, isLoading && styles.saveButtonDisabled]}
                onPress={handleChangePassword}
                disabled={isLoading}
              >
                {isLoading ? (
                  <ActivityIndicator size="small" color="#FFFFFF" />
                ) : (
                  <Text style={styles.saveButtonText}>{t.profile.save}</Text>
                )}
              </Pressable>
            </View>
          </View>
        )}
      </View>

      {/* 退出登录 */}
      <Pressable style={styles.logoutButton} onPress={onLogout}>
        <Text style={styles.logoutButtonText}>{t.login.logout}</Text>
      </Pressable>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F6F7FB' },
  content: { padding: 20, gap: 20 },
  header: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between', marginBottom: 10 },
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
  section: { gap: 12 },
  sectionHeader: { alignItems: 'center', flexDirection: 'row', gap: 8 },
  sectionTitle: { color: '#162033', fontSize: 16, fontWeight: '700' },
  card: {
    backgroundColor: '#FFFFFF',
    borderColor: '#E5E7EB',
    borderRadius: 12,
    borderWidth: 1,
    padding: 16,
  },
  label: { color: '#6B7280', fontSize: 13, marginBottom: 4 },
  value: { color: '#162033', fontSize: 16, fontWeight: '600' },
  languageOptions: { gap: 8 },
  languageOption: {
    alignItems: 'center',
    backgroundColor: '#FFFFFF',
    borderColor: '#E5E7EB',
    borderRadius: 8,
    borderWidth: 1,
    flexDirection: 'row',
    justifyContent: 'space-between',
    padding: 14,
  },
  languageOptionActive: { backgroundColor: '#E9FBF7', borderColor: '#0F8B8D' },
  languageOptionText: { color: '#162033', fontSize: 15 },
  languageOptionTextActive: { color: '#0F8B8D', fontWeight: '600' },
  changePasswordButton: {
    alignItems: 'center',
    backgroundColor: '#FFFFFF',
    borderColor: '#E5E7EB',
    borderRadius: 8,
    borderWidth: 1,
    flexDirection: 'row',
    gap: 10,
    padding: 14,
  },
  changePasswordButtonText: { color: '#0F8B8D', fontSize: 15, fontWeight: '600' },
  passwordForm: {
    backgroundColor: '#FFFFFF',
    borderColor: '#E5E7EB',
    borderRadius: 12,
    borderWidth: 1,
    gap: 16,
    padding: 16,
  },
  inputGroup: { gap: 6 },
  inputLabel: { color: '#374151', fontSize: 13, fontWeight: '500' },
  input: {
    backgroundColor: '#F8FAFC',
    borderColor: '#E5E7EB',
    borderRadius: 8,
    borderWidth: 1,
    color: '#162033',
    fontSize: 15,
    padding: 12,
  },
  strengthIndicator: { gap: 6, marginTop: 8 },
  strengthBar: { flexDirection: 'row', gap: 4 },
  strengthSegment: { borderRadius: 2, flex: 1, height: 4 },
  strengthLabel: { fontSize: 12 },
  requirements: {
    backgroundColor: '#F8FAFC',
    borderColor: '#E5E7EB',
    borderRadius: 8,
    borderWidth: 1,
    gap: 8,
    padding: 12,
  },
  requirementsTitle: { color: '#374151', fontSize: 13, fontWeight: '600', marginBottom: 4 },
  requirementItem: { alignItems: 'center', flexDirection: 'row', gap: 8 },
  checkCircle: {
    alignItems: 'center',
    backgroundColor: '#E5E7EB',
    borderRadius: 10,
    height: 18,
    justifyContent: 'center',
    width: 18,
  },
  checkCircleValid: { backgroundColor: '#10B981' },
  requirementText: { color: '#6B7280', fontSize: 12 },
  requirementTextValid: { color: '#10B981' },
  generateButton: {
    alignItems: 'center',
    borderColor: '#0F8B8D',
    borderRadius: 8,
    borderWidth: 1,
    flexDirection: 'row',
    gap: 8,
    justifyContent: 'center',
    padding: 12,
  },
  generateButtonText: { color: '#0F8B8D', fontSize: 14, fontWeight: '600' },
  errorBanner: {
    backgroundColor: '#FEF3F2',
    borderColor: '#FECACA',
    borderRadius: 8,
    borderWidth: 1,
    padding: 12,
  },
  errorText: { color: '#B42318', fontSize: 13 },
  successBanner: {
    backgroundColor: '#ECFDF5',
    borderColor: '#A7F3D0',
    borderRadius: 8,
    borderWidth: 1,
    padding: 12,
  },
  successText: { color: '#047857', fontSize: 13 },
  buttonRow: { flexDirection: 'row', gap: 12, marginTop: 8 },
  cancelButton: {
    alignItems: 'center',
    backgroundColor: '#FFFFFF',
    borderColor: '#E5E7EB',
    borderRadius: 8,
    borderWidth: 1,
    flex: 1,
    justifyContent: 'center',
    padding: 14,
  },
  cancelButtonText: { color: '#6B7280', fontSize: 15, fontWeight: '600' },
  saveButton: {
    alignItems: 'center',
    backgroundColor: '#0F8B8D',
    borderRadius: 8,
    flex: 1,
    justifyContent: 'center',
    padding: 14,
  },
  saveButtonDisabled: { opacity: 0.6 },
  saveButtonText: { color: '#FFFFFF', fontSize: 15, fontWeight: '700' },
  legalLinks: {
    flexDirection: 'row',
    gap: 12,
    justifyContent: 'space-between',
  },
  legalLinkButton: {
    flex: 1,
    alignItems: 'center',
    backgroundColor: '#FFFFFF',
    borderColor: '#E5E7EB',
    borderRadius: 8,
    borderWidth: 1,
    padding: 14,
  },
  legalLinkText: {
    color: '#0F8B8D',
    fontSize: 14,
    fontWeight: '600',
  },
  logoutButton: {
    alignItems: 'center',
    backgroundColor: '#FEF3F2',
    borderColor: '#FECACA',
    borderRadius: 8,
    borderWidth: 1,
    marginTop: 20,
    padding: 14,
  },
  logoutButtonText: { color: '#B42318', fontSize: 15, fontWeight: '600' },
});
