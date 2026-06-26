"use client";

import { useCallback, useEffect, useRef, useState } from "react";

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
  const bindingsRef = useRef<ImBinding[]>([]);

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

  const remove = useCallback(async (bindingId: number): Promise<boolean> => {
    // Optimistic update: drop the row from local state immediately
    // so the user sees the unbind take effect without a full
    // list-reload flicker. The list is reconciled from the server
    // in the background; if the DELETE fails we restore the row
    // and surface the error.
    const previousBindings = bindingsRef.current;
    const removedIndex = previousBindings.findIndex(
      (binding) => binding.id === bindingId,
    );
    const removedBinding =
      removedIndex >= 0 ? previousBindings[removedIndex] : null;
    if (removedBinding === null) {
      return false;
    }
    setError(null);
    setBindings((current) =>
      current.filter((binding) => binding.id !== bindingId),
    );
    try {
      await deleteBinding(bindingId);
      return true;
    } catch (err) {
      setBindings((current) => {
        if (current.some((binding) => binding.id === bindingId)) {
          return current;
        }
        const insertAt = Math.min(removedIndex, current.length);
        return [
          ...current.slice(0, insertAt),
          removedBinding,
          ...current.slice(insertAt),
        ];
      });
      setError(err instanceof Error ? err.message : "Failed to unbind");
      return false;
    }
  }, []);

  useEffect(() => {
    bindingsRef.current = bindings;
  }, [bindings]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { bindings, isLoading, error, refresh, generateCode, remove };
}
