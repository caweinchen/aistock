import { useState, useCallback } from 'react';
import { login as apiLogin } from '../services/api';
import { getAuthToken, setAuthToken, clearAuthToken, isLoggedIn as checkLoggedIn, setStoredUser } from '../services/storage';
import { useTranslation } from '../i18n';

export function useAuth() {
  const { t } = useTranslation();
  const [isLoggedIn, setIsLoggedIn] = useState(checkLoggedIn());
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const login = useCallback(async (username: string, password: string) => {
    setIsLoading(true);
    setError(null);

    try {
      const result = await apiLogin(username, password);
      setAuthToken(result.token);
      setStoredUser(result.username);
      setIsLoggedIn(true);
      return true;
    } catch (err) {
      const errorKey = err instanceof Error ? err.message : 'login';
      setError(t.error[errorKey as keyof typeof t.error] || t.error.login);
      return false;
    } finally {
      setIsLoading(false);
    }
  }, [t]);

  const logout = useCallback(() => {
    clearAuthToken();
    setIsLoggedIn(false);
    setError(null);
  }, []);

  const getToken = useCallback(() => {
    return getAuthToken();
  }, []);

  return {
    isLoggedIn,
    isLoading,
    error,
    login,
    logout,
    getToken,
  };
}