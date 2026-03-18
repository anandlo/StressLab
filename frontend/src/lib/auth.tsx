"use client";

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { getMe, loginUser, registerUser, refreshAuthToken, logoutUser } from "./api";
import type { User } from "./types";

const TOKEN_KEY = "stresslab_token";

interface AuthContextValue {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<{ mfa_required?: boolean; mfa_token?: string }>;
  logout: () => Promise<void>;
  setTokenAndUser: (token: string, user: User) => void;
  register: (email: string, password: string, phone?: string) => Promise<{ user_id: string; message: string }>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  // Rehydrate from localStorage on mount
  useEffect(() => {
    const stored = localStorage.getItem(TOKEN_KEY);
    if (stored) {
      getMe(stored)
        .then((u) => {
          setToken(stored);
          setUser(u);
        })
        .catch(() => {
          localStorage.removeItem(TOKEN_KEY);
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const result = await loginUser(email, password);
    if (result.mfa_required) {
      return { mfa_required: true, mfa_token: result.mfa_token };
    }
    if (result.access_token && result.user) {
      localStorage.setItem(TOKEN_KEY, result.access_token);
      setToken(result.access_token);
      setUser(result.user);
    }
    return {};
  }, []);

  const logout = useCallback(async () => {
    const currentToken = token;
    // Clear local state immediately so the UI responds without waiting
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setUser(null);
    // Tell the backend to increment token_version; swallow errors (e.g. already expired)
    if (currentToken) {
      try { await logoutUser(currentToken); } catch { /* ignore */ }
    }
  }, [token]);

  const setTokenAndUser = useCallback((t: string, u: User) => {
    localStorage.setItem(TOKEN_KEY, t);
    setToken(t);
    setUser(u);
  }, []);

  const register = useCallback(async (email: string, password: string, phone?: string) => {
    return registerUser(email, password, phone);
  }, []);

  const refreshUser = useCallback(async () => {
    if (!token) return;
    try {
      const u = await getMe(token);
      setUser(u);
    } catch {
      localStorage.removeItem(TOKEN_KEY);
      setToken(null);
      setUser(null);
    }
  }, [token]);

  // Silently refresh the access token every 50 minutes (token expires in 60)
  useEffect(() => {
    if (!token) return;
    const REFRESH_MS = 50 * 60 * 1000;
    const id = setInterval(async () => {
      try {
        const res = await refreshAuthToken(token);
        localStorage.setItem(TOKEN_KEY, res.access_token);
        setToken(res.access_token);
        setUser(res.user);
      } catch {
        // Token likely expired or invalid; force logout
        localStorage.removeItem(TOKEN_KEY);
        setToken(null);
        setUser(null);
      }
    }, REFRESH_MS);
    return () => clearInterval(id);
  }, [token]);

  return (
    <AuthContext.Provider value={{ user, token, loading, login, logout, setTokenAndUser, register, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
