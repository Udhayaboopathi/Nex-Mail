"use client";

import { useState, useEffect } from "react";
import { domainAdminApi } from "../lib/api";

export interface WhitelabelConfig {
  companyName: string;
  primaryColor: string;
  logoUrl: string;
}

interface WhitelabelRaw {
  whitelabel_company_name?: string;
  whitelabel_primary_color?: string;
  whitelabel_logo_url?: string;
}

export function useWhitelabel() {
  const [data, setData] = useState<WhitelabelConfig>({
    companyName: "Nex Mail",
    primaryColor: "#6366f1",
    logoUrl: "",
  });
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    domainAdminApi
      .getWhitelabel()
      .then((raw) => {
        const r = raw as WhitelabelRaw;
        setData({
          companyName: r.whitelabel_company_name ?? "Nex Mail",
          primaryColor: r.whitelabel_primary_color ?? "#6366f1",
          logoUrl: r.whitelabel_logo_url ?? "",
        });
      })
      .catch(() => undefined)
      .finally(() => setIsLoading(false));
  }, []);

  return { data, isLoading };
}
