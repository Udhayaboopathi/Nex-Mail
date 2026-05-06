import { create } from "zustand";
import type { Role } from "../types";

interface UserSession {
  token: string;
  email: string;
  role: Role;
}

interface AppState {
  session: UserSession | null;
  darkMode: boolean;
  composeOpen: boolean;
  setSession: (s: UserSession | null) => void;
  setDarkMode: (v: boolean) => void;
  setComposeOpen: (v: boolean) => void;
}

export const useAppStore = create<AppState>((set) => ({
  session: null,
  darkMode: false,
  composeOpen: false,
  setSession: (session) => set({ session }),
  setDarkMode: (darkMode) => set({ darkMode }),
  setComposeOpen: (composeOpen) => set({ composeOpen }),
}));
