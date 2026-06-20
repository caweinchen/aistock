import { SafeAreaView, StyleSheet } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { useState, useRef, useEffect } from 'react';
import { I18nProvider } from './src/i18n';
import { HomeScreen } from './src/pages/HomeScreen';
import { LoginScreen } from './src/pages/LoginScreen';
import { SettingsScreen } from './src/pages/SettingsScreen';
import { ProfileScreen } from './src/pages/ProfileScreen';
import { isLoggedIn as checkLoggedIn, clearAuthToken } from './src/services/storage';

type Screen = 'home' | 'settings' | 'login-settings' | 'profile';

export default function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [currentScreen, setCurrentScreen] = useState<Screen>('home');
  const [refreshKey, setRefreshKey] = useState(0);

  // 检查登录状态
  useEffect(() => {
    setIsLoggedIn(checkLoggedIn());
  }, []);

  const goToSettings = () => setCurrentScreen('settings');
  const goToHome = () => setCurrentScreen('home');
  const goToLoginSettings = () => setCurrentScreen('login-settings');
  const goToProfile = () => setCurrentScreen('profile');

  const handleLoginSuccess = () => {
    setIsLoggedIn(true);
    setCurrentScreen('home');
  };

  const handleLogout = () => {
    clearAuthToken();
    setIsLoggedIn(false);
    setCurrentScreen('home');
  };

  const handleConfigSaved = () => {
    setRefreshKey(prev => prev + 1);
  };

  // 未登录显示登录页面或登录设置页面
  if (!isLoggedIn) {
    return (
      <I18nProvider>
        <SafeAreaView style={styles.safeArea}>
          <StatusBar style="dark" />
          {currentScreen === 'login-settings' ? (
            <SettingsScreen
              onBack={() => setCurrentScreen('home')}
              onConfigSaved={handleConfigSaved}
            />
          ) : (
            <LoginScreen onSuccess={handleLoginSuccess} onOpenSettings={goToLoginSettings} />
          )}
        </SafeAreaView>
      </I18nProvider>
    );
  }

  // 已登录显示主页面
  const renderScreen = () => {
    switch (currentScreen) {
      case 'profile':
        return (
          <ProfileScreen onBack={goToHome} onLogout={handleLogout} />
        );
      case 'settings':
        return (
          <SettingsScreen onBack={goToHome} onConfigSaved={handleConfigSaved} />
        );
      case 'home':
      default:
        return (
          <HomeScreen
            key={refreshKey}
            onOpenSettings={goToSettings}
            onOpenProfile={goToProfile}
            onLogout={handleLogout}
          />
        );
    }
  };

  return (
    <I18nProvider>
      <SafeAreaView style={styles.safeArea}>
        <StatusBar style="dark" />
        {renderScreen()}
      </SafeAreaView>
    </I18nProvider>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: '#F6F7FB',
  },
});