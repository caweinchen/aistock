import { useState, useCallback, useEffect } from 'react';
import { login as apiLogin, verifyToken } from '../services/api';
import { getAuthToken, setAuthToken, clearAuthToken, setStoredUser, clearOfflineLogin, setUserId, setStoredUserRole, getStoredUserRole } from '../services/storage';
import { getInitialAuthState } from '../services/authSession';
import { useTranslation } from '../i18n';

export function useAuth() {
  const { t } = useTranslation();
  const [isLoggedIn, setIsLoggedIn] = useState<boolean>(getInitialAuthState());
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isOfflineMode, setIsOfflineMode] = useState(false);
  const [tokenValidationFailed, setTokenValidationFailed] = useState(false);
  const [role, setRole] = useState<string | null>(() => getStoredUserRole());

  useEffect(() => {
    if (!isLoggedIn) return;
    
    const token = getAuthToken();
    if (token && token.startsWith('offline_')) {
      setIsOfflineMode(true);
    }
  }, [isLoggedIn]);

  const login = useCallback(async (username: string, password: string) => {
    setIsLoading(true);
    setError(null);
    setIsOfflineMode(false);
    setTokenValidationFailed(false);

    try {
      const result = await apiLogin(username, password);
      setAuthToken(result.token);
      setStoredUser(result.username);
      setUserId(String(result.user_id || result.username));
      setStoredUserRole(result.role);
      setRole(result.role);
      setIsLoggedIn(true);
      
      if (result.isOffline) {
        setIsOfflineMode(true);
        console.log('Logged in offline mode');
      } else {
        console.log('Logged in online mode');
      }
      
      return { success: true, isOffline: !!result.isOffline };
    } catch (err) {
      const errorKey = err instanceof Error ? err.message : 'login';
      setError(t.error[errorKey as keyof typeof t.error] || t.error.login);
      return { success: false, isOffline: false };
    } finally {
      setIsLoading(false);
    }
  }, [t]);

  const logout = useCallback(() => {
    clearAuthToken();
    clearOfflineLogin();
    setIsLoggedIn(false);
    setError(null);
    setIsOfflineMode(false);
    setTokenValidationFailed(false);
    setRole(null);
  }, []);

  const validateTokenWithServer = useCallback(async (): Promise<boolean> => {
    try {
      const result = await verifyToken();
      if (!result.valid) {
        if (!result.isOffline) {
          setTokenValidationFailed(true);
          logout();
          return false;
        }
      } else {
        if (result.role) {
          setRole(result.role);
          setStoredUserRole(result.role);
        }
        setIsOfflineMode(false);
      }
      return result.valid;
    } catch {
      return false;
    }
  }, [logout]);

  const handleTokenInvalid = useCallback(() => {
    setTokenValidationFailed(true);
    logout();
  }, [logout]);

  const getToken = useCallback(() => {
    return getAuthToken();
  }, []);

  return {
    isLoggedIn,
    isLoading,
    error,
    isOfflineMode,
    role,
    isAdmin: role === 'admin',
    tokenValidationFailed,
    login,
    logout,
    getToken,
    validateTokenWithServer,
    handleTokenInvalid,
  };
}
