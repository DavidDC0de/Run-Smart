import { createContext, useContext, useState, type ReactNode } from "react";
import { clearToken, getToken, setToken } from "./api/client";

type AuthValue = {
  isLoggedIn: boolean;
  signIn: (token: string) => void;
  signOut: () => void;
};

const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setTokenState] = useState<string | null>(getToken());

  const value: AuthValue = {
    isLoggedIn: token !== null,
    signIn: (newToken) => {
      setToken(newToken);
      setTokenState(newToken);
    },
    signOut: () => {
      clearToken();
      setTokenState(null);
    },
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}