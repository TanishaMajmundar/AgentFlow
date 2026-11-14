import { createContext, useCallback, useContext, useMemo, useState } from "react";

// DEMO AUTH — there is no auth endpoint in the current backend plan, so this stores a
// fake session in localStorage. When the backend adds auth, replace the bodies of
// login() / signup() with real API calls and store the returned token in "af_token".

const AuthContext = createContext(null);
const KEY = "af_user";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try { return JSON.parse(localStorage.getItem(KEY)); } catch { return null; }
  });

  const persist = (u) => { localStorage.setItem(KEY, JSON.stringify(u)); setUser(u); return u; };

  const login = useCallback(async ({ email }) => {
    await sleep(600);
    return persist({ name: email.split("@")[0], email });
  }, []);

  const signup = useCallback(async ({ name, email }) => {
    await sleep(700);
    return persist({ name, email });
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(KEY);
    localStorage.removeItem("af_token");
    setUser(null);
  }, []);

  const value = useMemo(() => ({ user, login, signup, logout }), [user, login, signup, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
