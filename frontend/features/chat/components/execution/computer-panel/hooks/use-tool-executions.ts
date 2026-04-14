"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  getRunToolExecutionsAction,
  getRunToolExecutionsDeltaAction,
} from "@/features/chat/actions/query-actions";
import type { ToolExecutionResponse } from "@/features/chat/types";

interface UseToolExecutionsOptions {
  runId?: string;
  isActive?: boolean;
  pollingIntervalMs?: number;
  limit?: number;
}

export function useToolExecutions({
  runId,
  isActive = false,
  pollingIntervalMs = 2000,
  limit = 500,
}: UseToolExecutionsOptions) {
  const [executions, setExecutions] = useState<ToolExecutionResponse[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const lastRunIdRef = useRef<string | null>(null);
  const hasLoadedOnceRef = useRef(false);
  const requestSeqRef = useRef(0);
  const prevIsActiveRef = useRef(isActive);
  const cursorRef = useRef<{ afterCreatedAt?: string; afterId?: string }>({});

  const mergeById = useCallback(
    (base: ToolExecutionResponse[], incoming: ToolExecutionResponse[]) => {
      if (incoming.length === 0) return base;
      const byId = new Map(base.map((item) => [item.id, item]));
      for (const item of incoming) {
        // Delta can carry updates to an existing execution row. Keep the latest payload.
        byId.set(item.id, item);
      }
      const merged = Array.from(byId.values());
      merged.sort((a, b) => {
        if (a.created_at === b.created_at) {
          return a.id.localeCompare(b.id);
        }
        return a.created_at.localeCompare(b.created_at);
      });
      return merged;
    },
    [],
  );

  const updateCursor = useCallback((items: ToolExecutionResponse[]) => {
    if (items.length === 0) {
      cursorRef.current = {};
      return;
    }

    let latest = items[0];
    for (let i = 1; i < items.length; i += 1) {
      const current = items[i];
      if (current.updated_at > latest.updated_at) {
        latest = current;
        continue;
      }
      if (
        current.updated_at === latest.updated_at &&
        current.id.localeCompare(latest.id) > 0
      ) {
        latest = current;
      }
    }

    cursorRef.current = {
      afterCreatedAt: latest.updated_at,
      afterId: latest.id,
    };
  }, []);

  const fetchSnapshot = useCallback(
    async (replace = false) => {
      if (!runId) return;
      const seq = (requestSeqRef.current += 1);
      const shouldShowLoading = !hasLoadedOnceRef.current && replace;
      if (shouldShowLoading) {
        setIsLoading(true);
      }

      const offset = replace ? 0 : executions.length;

      try {
        const data = await getRunToolExecutionsAction({
          runId,
          limit,
          offset,
        });
        if (seq !== requestSeqRef.current) return;

        if (replace) {
          setExecutions(data);
          updateCursor(data);
        } else {
          const merged = mergeById(executions, data);
          setExecutions(merged);
          updateCursor(merged);
        }

        setHasMore(data.length === limit);
        setError(null);
      } catch (err) {
        if (seq !== requestSeqRef.current) return;
        setError(err as Error);
      } finally {
        if (seq !== requestSeqRef.current) return;
        setIsLoading(false);
        setIsLoadingMore(false);
        hasLoadedOnceRef.current = true;
      }
    },
    [executions, limit, mergeById, runId, updateCursor],
  );

  const fetchDelta = useCallback(async () => {
    if (!runId) return;
    const seq = requestSeqRef.current;
    const { afterCreatedAt, afterId } = cursorRef.current;
    if (!afterCreatedAt) {
      await fetchSnapshot(true);
      return;
    }

    try {
      const appended: ToolExecutionResponse[] = [];
      let currentCreatedAt = afterCreatedAt;
      let currentId = afterId;
      let hasMore = true;
      let guard = 0;

      // Drain a few pages in one poll cycle to catch up quickly after bursts.
      while (hasMore && guard < 5) {
        const payload = await getRunToolExecutionsDeltaAction({
          runId,
          afterCreatedAt: currentCreatedAt,
          afterId: currentId,
          limit,
        });
        appended.push(...payload.items);
        hasMore = payload.has_more;
        currentCreatedAt =
          payload.next_after_created_at ??
          payload.items.at(-1)?.updated_at ??
          currentCreatedAt;
        currentId = payload.next_after_id ?? payload.items.at(-1)?.id;
        if (!currentCreatedAt || !currentId) break;
        guard += 1;
      }

      if (seq !== requestSeqRef.current) return;
      if (appended.length === 0) return;

      cursorRef.current = {
        afterCreatedAt: currentCreatedAt,
        afterId: currentId,
      };
      setExecutions((prev) => {
        return mergeById(prev, appended);
      });
      setError(null);
    } catch (err) {
      if (seq !== requestSeqRef.current) return;
      setError(err as Error);
    }
  }, [fetchSnapshot, limit, mergeById, runId]);

  const loadMore = useCallback(() => {
    if (isLoadingMore || !hasMore || !runId) return;
    setIsLoadingMore(true);
    void fetchSnapshot(false);
  }, [fetchSnapshot, hasMore, isLoadingMore, runId]);

  // Reset state when run changes.
  useEffect(() => {
    if (!runId) return;
    if (lastRunIdRef.current === runId) return;
    lastRunIdRef.current = runId;
    hasLoadedOnceRef.current = false;
    requestSeqRef.current += 1;
    setExecutions([]);
    setError(null);
    setIsLoading(false);
    setIsLoadingMore(false);
    setHasMore(true);
    cursorRef.current = {};
    void fetchSnapshot(true);
  }, [fetchSnapshot, runId]);

  // Poll while active.
  useEffect(() => {
    if (!runId) return;
    if (!isActive) return;
    const id = setInterval(() => {
      void fetchDelta();
    }, pollingIntervalMs);
    return () => clearInterval(id);
  }, [fetchDelta, isActive, pollingIntervalMs, runId]);

  // When a session transitions from active -> terminal, fetch once more so the UI
  // can pick up the final tool_output written during cancellation/failure.
  useEffect(() => {
    if (!runId) return;
    const wasActive = prevIsActiveRef.current;
    prevIsActiveRef.current = isActive;
    if (wasActive && !isActive) {
      void fetchDelta();
    }
  }, [fetchDelta, isActive, runId]);

  return {
    executions,
    isLoading,
    isLoadingMore,
    hasMore,
    error,
    refetch: () => fetchSnapshot(true),
    loadMore,
  };
}
