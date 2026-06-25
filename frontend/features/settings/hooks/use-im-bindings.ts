"use client";

import { useCallback, useEffect, useState } from "react";

import {
  createBindingCode,
  deleteBinding,
  listMyBindings,
  type BindingCode,
  type ImBinding,
  type ImBindingProvider,
} from "@/features/settings/api/im-bindings-api";

interface UseImBindings {
  bindings: ImBinding[];
  isLoading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  generateCode: (
    provider: ImBindingProvider | null,
  ) => Promise<BindingCode | null>;
  remove: (bindingId: number) => Promise<boolean>;
}

export function useImBindings(): UseImBindings {
  const [bindings, setBindings] = useState<ImBinding[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const rows = await listMyBindings();
      setBindings(rows);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load bindings");
    } finally {
      setIsLoading(false);
    }
  }, []);

  const generateCode = useCallback(
    async (provider: ImBindingProvider | null): Promise<BindingCode | null> => {
      try {
        return await createBindingCode(provider);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Failed to generate code",
        );
        return null;
      }
    },
    [],
  );

  const remove = useCallback(
    async (bindingId: number): Promise<boolean> => {
      try {
        await deleteBinding(bindingId);
        await refresh();
        return true;
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to unbind");
        return false;
      }
    },
    [refresh],
  );

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { bindings, isLoading, error, refresh, generateCode, remove };
}
