"use client";

import { useMemo } from "react";
import { getToken, getRole } from "../lib/auth";
import type { Role } from "../types";

export function useAuth(): { isAuthenticated: boolean; token: string | null; role: Role | null } {
  const token = getToken();
  const role = getRole();
  return useMemo(() => ({ isAuthenticated: Boolean(token), token, role }), [token, role]);
}
