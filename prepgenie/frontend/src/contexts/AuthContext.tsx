import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { User, LoginRequest, RegisterRequest } from '../types';
import { apiService } from '../services/api';

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (credentials: LoginRequest) => Promise<void>;
  register: (userData: RegisterRequest) => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  // Define logout function with useCallback to prevent dependency issues
  const logout = useCallback(() => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    setUser(null);
  }, []);

  useEffect(() => {
    const initializeAuth = async () => {
      const token = localStorage.getItem('access_token');
      const savedUser = localStorage.getItem('user');

      if (token && savedUser) {
        try {
          setUser(JSON.parse(savedUser));
          // Verify token is still valid
          await apiService.getCurrentUser();
        } catch (error) {
          console.error('Token validation failed:', error);
          localStorage.removeItem('access_token');
          localStorage.removeItem('user');
          setUser(null);
        }
      }
      setLoading(false);
    };

    initializeAuth();
  }, []);

  // Auto-logout when ALL browser windows close (improved approach)
  useEffect(() => {
    // Track if user is authenticated in this tab
    const handleStorageChange = (e: StorageEvent) => {
      // Listen for auth changes from other tabs
      if (e.key === 'access_token' && e.newValue === null) {
        // Another tab logged out, sync this tab
        setUser(null);
      } else if (e.key === 'access_token' && e.newValue) {
        // Another tab logged in, sync this tab
        const savedUser = localStorage.getItem('user');
        if (savedUser) {
          setUser(JSON.parse(savedUser));
        }
      }
    };

    const handleVisibilityChange = () => {
      // Auto-logout when tab becomes hidden for too long (30 minutes)
      if (document.hidden && user) {
        const logoutTimer = setTimeout(() => {
          if (document.hidden) {
            logout();
          }
        }, 30 * 60 * 1000); // 30 minutes

        // Clear timeout when tab becomes visible again
        const handleVisibilityShow = () => {
          if (!document.hidden) {
            clearTimeout(logoutTimer);
            document.removeEventListener('visibilitychange', handleVisibilityShow);
          }
        };
        document.addEventListener('visibilitychange', handleVisibilityShow);
      }
    };

    // Listen for storage changes from other tabs
    window.addEventListener('storage', handleStorageChange);
    document.addEventListener('visibilitychange', handleVisibilityChange);

    // Cleanup
    return () => {
      window.removeEventListener('storage', handleStorageChange);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [user, logout]);

  const login = async (credentials: LoginRequest) => {
    try {
      const response = await apiService.login(credentials);
      localStorage.setItem('access_token', response.access_token);
      localStorage.setItem('user', JSON.stringify(response.user));
      setUser(response.user);
    } catch (error) {
      console.error('Login failed:', error);
      throw error;
    }
  };

  const register = async (userData: RegisterRequest) => {
    try {
      // Just call the registration API, don't auto-login
      await apiService.register(userData);
      // Don't set user state or store tokens - user needs to login manually
    } catch (error) {
      console.error('Registration failed:', error);
      throw error;
    }
  };

  const value: AuthContextType = {
    user,
    loading,
    login,
    register,
    logout,
    isAuthenticated: !!user,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};