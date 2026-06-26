/**
 * Server-scoped IM channel bindings API client.
 *
 * Wraps ``GET /api/v1/servers/{serverId}/im-channels`` to power the
 * "Linked IM chats" panel in the server detail page. The server
 * detail page lets members see which IM chats are currently
 * linked, so they can avoid sending sensitive content to the wrong
 * group.
 */

import { API_ENDPOINTS } from "@/services/api-client";

export type ImChannelProvider = "feishu" | "dingtalk" | "telegram" | string;
export type ImChannelChatType = "p2p" | "group" | string;

export interface ServerImChannel {
  id: number;
  provider: ImChannelProvider;
  destination: string;
  chat_type: ImChannelChatType;
  enabled: boolean;
  last_bound_by_user_id: string | null;
  last_bound_at: string | null;
}

interface Envelope<T> {
  code: number;
  message: string;
  data: T;
}

async function readEnvelope<T>(res: Response): Promise<T> {
  const body = (await res.json()) as Envelope<T>;
  if (!res.ok || body.code !== 0) {
    throw new Error(body.message || `HTTP ${res.status}`);
  }
  return body.data;
}

export async function listServerImChannels(
  serverId: string,
  fetchImpl: typeof fetch = fetch,
): Promise<ServerImChannel[]> {
  const res = await fetchImpl(
    `/api/v1${API_ENDPOINTS.serverImChannels(serverId)}`,
    {
      credentials: "include",
    },
  );
  return readEnvelope<ServerImChannel[]>(res);
}
