"use client";

import { useState, useEffect } from "react";
import { domainAdminApi } from "../lib/api";
import type { Mailbox } from "../types";

export function useMailboxes() {
  const [data, setData] = useState<Mailbox[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    domainAdminApi.getMailboxes()
      .then((res) => setData(res.items))
      .catch((e) => setError((e as Error).message))
      .finally(() => setIsLoading(false));
  }, []);

  return { data, isLoading, error };
}
