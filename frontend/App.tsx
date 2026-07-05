import { Pressable, SafeAreaView, StyleSheet, Text, TextInput, View } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { useState, useEffect } from 'react';
import { Bell, Globe, LogOut, Search, Settings, ShieldCheck, TrendingUp, User, X, Wifi, WifiOff } from 'lucide-react-native';
import { I18nProvider, useTranslation, type Locale } from './src/i18n';
import { initStorage } from './src/services/storage';
import { HomeScreen } from './src/pages/HomeScreen';
import { LoginScreen } from './src/pages/LoginScreen';
import { SettingsScreen } from './src/pages/SettingsScreen';
import { ProfileScreen } from './src/pages/ProfileScreen';
import { LegalScreen } from './src/pages/LegalScreen';
import { StockDetailScreen } from './src/pages/StockDetailScreen';
import { UserManagementScreen } from './src/pages/UserManagementScreen';
import { clearAuthToken, getStoredUser, getStoredUserRole, getUserId } from './src/services/storage';
import { getStartupRouteState } from './src/services/startupRoute';
import { createSessionResetState, createUserSessionKey } from './src/services/sessionState';
import type { ResearchSnapshot } from './src/types';

type Screen = 'login' | 'home' | 'settings' | 'login-settings' | 'profile' | 'stock-detail' | 'terms' | 'privacy' | 'user-management';

type LegalType = 'terms' | 'privacy';

interface ScreenParams {
  stockCode?: string;
  legalType?: LegalType;
}

export default function App() {
  const [isInitialized, setIsInitialized] = useState(false);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [currentScreen, setCurrentScreen] = useState<Screen>('login');
  const [screenParams, setScreenParams] = useState<ScreenParams>({});
  const [refreshKey, setRefreshKey] = useState(0);
  const [isSearchVisible, setIsSearchVisible] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [pendingSearchQuery, setPendingSearchQuery] = useState<string | null>(null);
  const [selectedStockCode, setSelectedStockCode] = useState<string | undefined>();
  const [researchSnapshot, setResearchSnapshot] = useState<ResearchSnapshot | null>(null);
  const [tokenInvalid, setTokenInvalid] = useState(false);
  const [isAdmin, setIsAdmin] = useState(false);
  const [sessionKey, setSessionKey] = useState(() => createUserSessionKey(getStoredUser(), getUserId()));
  const [isOffline, setIsOffline] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        await initStorage();
      } catch {
        // ignore init errors
      }
      const startupRouteState = getStartupRouteState();
      setIsLoggedIn(startupRouteState.isLoggedIn);
      setCurrentScreen(startupRouteState.currentScreen);
      setIsInitialized(true);
    })();
  }, []);

  useEffect(() => {
    if (tokenInvalid) {
      handleLogout();
    }
  }, [tokenInvalid]);

  const goToSettings = () => setCurrentScreen('settings');
  const goToHome = () => {
    setCurrentScreen('home');
    setScreenParams({});
    setTokenInvalid(false);
  };
  const goToLoginSettings = () => setCurrentScreen('login-settings');
  const goToProfile = () => setCurrentScreen('profile');
  const goToUserManagement = () => {
    if (isAdmin) setCurrentScreen('user-management');
  };
  const goToTerms = () => {
    setCurrentScreen('terms');
    setScreenParams({ legalType: 'terms' });
  };
  const goToPrivacy = () => {
    setCurrentScreen('privacy');
    setScreenParams({ legalType: 'privacy' });
  };
  
  const goToStockDetail = (stockCode: string) => {
    setSelectedStockCode(stockCode);
    setScreenParams({ stockCode });
    setCurrentScreen('stock-detail');
  };

  const handleLoginSuccess = (state?: { isOffline?: boolean }) => {
    const resetState = createSessionResetState(refreshKey);
    setIsLoggedIn(true);
    setIsAdmin(getStoredUserRole() === 'admin');
    setIsOffline(state?.isOffline ?? false);
    setSessionKey(createUserSessionKey(getStoredUser(), getUserId()));
    setScreenParams(resetState.screenParams);
    setRefreshKey(resetState.refreshKey);
    setIsSearchVisible(resetState.isSearchVisible);
    setSearchQuery(resetState.searchQuery);
    setPendingSearchQuery(resetState.pendingSearchQuery);
    setSelectedStockCode(resetState.selectedStockCode);
    setResearchSnapshot(resetState.researchSnapshot);
    setCurrentScreen('home');
    setTokenInvalid(false);
  };

  const handleLogout = () => {
    const resetState = createSessionResetState(refreshKey);
    clearAuthToken();
    setIsLoggedIn(false);
    setIsAdmin(false);
    setSessionKey(createUserSessionKey(null, null));
    setScreenParams(resetState.screenParams);
    setRefreshKey(resetState.refreshKey);
    setIsSearchVisible(resetState.isSearchVisible);
    setSearchQuery(resetState.searchQuery);
    setPendingSearchQuery(resetState.pendingSearchQuery);
    setSelectedStockCode(resetState.selectedStockCode);
    setResearchSnapshot(resetState.researchSnapshot);
    setCurrentScreen('login');
    setTokenInvalid(false);
  };

  const handleConfigSaved = () => {
    setRefreshKey(prev => prev + 1);
  };

  const handleSubmitSearch = () => {
    setPendingSearchQuery(searchQuery);
    setCurrentScreen('home');
  };

  const handleToggleSearch = () => {
    setCurrentScreen('home');
    setIsSearchVisible((visible) => !visible);
  };

  const handleClearSearch = () => {
    setSearchQuery('');
    setPendingSearchQuery('');
    setCurrentScreen('home');
  };

  const handleTokenInvalid = () => {
    setTokenInvalid(true);
  };

  // Show loading state while initializing
  if (!isInitialized) {
    return (
      <I18nProvider>
        <SafeAreaView style={styles.safeArea}>
          <StatusBar style="dark" />
          <View style={styles.loadingContainer}>
            <Text style={styles.loadingText}>Loading...</Text>
          </View>
        </SafeAreaView>
      </I18nProvider>
    );
  }

  // Show login screen when not logged in
  if (!isLoggedIn) {
    return (
      <I18nProvider>
        <SafeAreaView style={styles.safeArea}>
          <StatusBar style="dark" />
          {currentScreen === 'login-settings' ? (
            <SettingsScreen
              onBack={() => setCurrentScreen('login')}
              onConfigSaved={handleConfigSaved}
            />
          ) : currentScreen === 'terms' || currentScreen === 'privacy' ? (
            <LegalScreen
              type={screenParams.legalType ?? 'terms'}
              onBack={() => {
                setCurrentScreen('login');
                setScreenParams({});
              }}
            />
          ) : (
            <LoginScreen
              onSuccess={handleLoginSuccess}
              onOpenSettings={goToLoginSettings}
              onOpenTerms={goToTerms}
              onOpenPrivacy={goToPrivacy}
            />
          )}
        </SafeAreaView>
      </I18nProvider>
    );
  }

  const renderScreen = () => {
    switch (currentScreen) {
      case 'profile':
        return (
          <ProfileScreen onBack={goToHome} onLogout={handleLogout} onOpenTerms={goToTerms} onOpenPrivacy={goToPrivacy} />
        );
      case 'settings':
        return (
          <SettingsScreen onBack={goToHome} onConfigSaved={handleConfigSaved} />
        );
      case 'user-management':
        return <UserManagementScreen isAdmin={isAdmin} onBack={goToHome} />;
      case 'terms':
      case 'privacy':
        return (
          <LegalScreen
            type={screenParams.legalType ?? 'terms'}
            onBack={goToHome}
          />
        );
      case 'stock-detail':
        return (
          <StockDetailScreen
            stockCode={screenParams.stockCode || ''}
            onBack={goToHome}
            onTokenInvalid={handleTokenInvalid}
            researchSnapshot={researchSnapshot}
            onResearchSnapshotChange={setResearchSnapshot}
          />
        );
      case 'home':
      default:
        return (
          <HomeScreen
            key={`${sessionKey}:${refreshKey}`}
            pendingSearchQuery={pendingSearchQuery}
            selectedStockCode={selectedStockCode}
            onSelectedStockCodeChange={setSelectedStockCode}
            onResearchSnapshotChange={setResearchSnapshot}
            onOpenSettings={goToSettings}
            onOpenProfile={goToProfile}
            onLogout={handleLogout}
            onOpenStockDetail={goToStockDetail}
            onTokenInvalid={handleTokenInvalid}
            onOfflineChange={setIsOffline}
            onWatchlistUpdated={handleClearSearch}
          />
        );
    }
  };

  return (
    <I18nProvider>
      <SafeAreaView style={styles.safeArea}>
        <StatusBar style="dark" />
        <View style={styles.appShell}>
          {currentScreen !== 'login-settings' && (
            <AppHeader
              onOpenSettings={goToSettings}
              onOpenProfile={goToProfile}
              onOpenUserManagement={goToUserManagement}
              onLogout={handleLogout}
              onToggleSearch={handleToggleSearch}
              isAdmin={isAdmin}
              isOffline={isOffline}
            />
          )}
          {isSearchVisible && currentScreen !== 'login-settings' && (
            <SearchPanel
              searchQuery={searchQuery}
              onChangeSearchQuery={setSearchQuery}
              onSubmitSearch={handleSubmitSearch}
              onClearSearch={handleClearSearch}
            />
          )}
          <View style={styles.screenSlot}>{renderScreen()}</View>
        </View>
      </SafeAreaView>
    </I18nProvider>
  );
}

function AppHeader({
  onOpenSettings,
  onOpenProfile,
  onOpenUserManagement,
  onLogout,
  onToggleSearch,
  isAdmin,
  isOffline,
}: {
  onOpenSettings: () => void;
  onOpenProfile: () => void;
  onOpenUserManagement: () => void;
  onLogout: () => void;
  onToggleSearch: () => void;
  isAdmin: boolean;
  isOffline: boolean;
}) {
  const { t, locale, setLocale } = useTranslation();
  const localeLabel = locale === 'zh' ? '中' : locale === 'zh-Hant' ? '繁' : 'EN';

  return (
    <View style={styles.header}>
      <View style={styles.headerIconBlock}>
        <View style={styles.appIcon}>
          <TrendingUp size={24} color="#FFFFFF" />
        </View>
      </View>
      <View style={styles.headerActions}>
        <View style={styles.connectionStatus}>
          {isOffline ? (
            <WifiOff size={18} color="#DC2626" />
          ) : (
            <Wifi size={18} color="#10B981" />
          )}
          <Text style={[styles.connectionStatusText, isOffline ? styles.connectionStatusOffline : styles.connectionStatusOnline]}>
            {isOffline ? t.common.offline : t.common.online}
          </Text>
        </View>
        <Pressable onPress={onToggleSearch}>
          <Search size={20} color="#162033" />
        </Pressable>
        <Pressable>
          <Bell size={20} color="#162033" />
        </Pressable>
        <Pressable onPress={onOpenSettings}>
          <Settings size={20} color="#162033" />
        </Pressable>
        <Pressable onPress={onOpenProfile}>
          <User size={20} color="#162033" />
        </Pressable>
        {isAdmin ? (
          <Pressable onPress={onOpenUserManagement}>
            <ShieldCheck size={20} color="#162033" />
          </Pressable>
        ) : null}
        <Pressable onPress={onLogout}>
          <LogOut size={20} color="#162033" />
        </Pressable>
        <Pressable
          accessibilityLabel={t.common.switchLanguage}
          accessibilityRole="button"
          style={styles.langButton}
          onPress={() => {
            const locales: Locale[] = ['zh', 'zh-Hant', 'en'];
            const currentIndex = locales.indexOf(locale);
            const nextLocale = locales[(currentIndex + 1) % locales.length];
            setLocale(nextLocale);
          }}
        >
          <Globe size={15} color="#FFFFFF" />
          <Text style={styles.langButtonText}>{localeLabel}</Text>
        </Pressable>
      </View>
    </View>
  );
}

function SearchPanel({
  searchQuery,
  onChangeSearchQuery,
  onSubmitSearch,
  onClearSearch,
}: {
  searchQuery: string;
  onChangeSearchQuery: (query: string) => void;
  onSubmitSearch: () => void;
  onClearSearch: () => void;
}) {
  const { t } = useTranslation();

  return (
    <View style={styles.searchPanel}>
      <Search size={18} color="#6B7280" />
      <TextInput
        style={styles.searchInput}
        value={searchQuery}
        onChangeText={onChangeSearchQuery}
        onSubmitEditing={onSubmitSearch}
        placeholder={t.stock.search}
        placeholderTextColor="#9CA3AF"
      />
      {searchQuery ? (
        <Pressable onPress={onClearSearch}>
          <X size={16} color="#6B7280" />
        </Pressable>
      ) : null}
      <Pressable style={styles.searchButton} onPress={onSubmitSearch}>
        <Text style={styles.searchButtonText}>{t.common.ok}</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: '#F6F7FB',
  },
  appShell: {
    flex: 1,
    gap: 12,
    paddingHorizontal: 20,
    paddingTop: 20,
  },
  screenSlot: {
    flex: 1,
    marginHorizontal: -20,
  },
  loadingContainer: {
    alignItems: 'center',
    flex: 1,
    justifyContent: 'center',
  },
  loadingText: {
    color: '#6B7280',
    fontSize: 14,
  },
  header: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: 12,
    justifyContent: 'space-between',
  },
  headerIconBlock: {
    flex: 1,
    minWidth: 0,
  },
  appIcon: {
    alignItems: 'center',
    backgroundColor: '#0F8B8D',
    borderRadius: 12,
    height: 44,
    justifyContent: 'center',
    width: 44,
  },
  headerActions: {
    alignItems: 'center',
    flexDirection: 'row',
    flexShrink: 0,
    gap: 8,
  },
  connectionStatus: {
    alignItems: 'center',
    flexDirection: 'row',
    gap: 4,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
    backgroundColor: '#F3F4F6',
  },
  connectionStatusText: {
    fontSize: 12,
    fontWeight: '600',
  },
  connectionStatusOnline: {
    color: '#10B981',
  },
  connectionStatusOffline: {
    color: '#DC2626',
  },
  langButton: {
    alignItems: 'center',
    backgroundColor: '#0F8B8D',
    borderRadius: 8,
    flexDirection: 'row',
    gap: 5,
    height: 36,
    justifyContent: 'center',
    minWidth: 58,
    paddingHorizontal: 10,
  },
  langButtonText: {
    color: '#FFFFFF',
    fontSize: 13,
    fontWeight: '800',
  },
  searchPanel: {
    alignItems: 'center',
    backgroundColor: '#FFFFFF',
    borderColor: '#D8DEE9',
    borderRadius: 8,
    borderWidth: 1,
    flexDirection: 'row',
    gap: 8,
    minHeight: 48,
    paddingHorizontal: 12,
  },
  searchInput: {
    color: '#162033',
    flex: 1,
    fontSize: 15,
    minWidth: 0,
    paddingVertical: 8,
  },
  searchButton: {
    alignItems: 'center',
    backgroundColor: '#0F8B8D',
    borderRadius: 8,
    height: 34,
    justifyContent: 'center',
    paddingHorizontal: 12,
  },
  searchButtonText: {
    color: '#FFFFFF',
    fontSize: 13,
    fontWeight: '800',
  },
});
