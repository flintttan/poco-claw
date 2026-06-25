"use client";

/**
 * IM bindings API client.
 *
 * Wraps the /api/v1/me/binding-codes and /api/v1/me/bindings
 * endpoints exposed by the backend. The Settings → Connections tab
 * uses this to list the user's current IM identities, mint a fresh
 * single-use binding code, and unbind an identity.
 */

export type ImBindingProvider = "feishu" | "dingtalk" | "telegram";

export interface ImBinding {
  id: number;
  provider: ImBindingProvider | string;
  im_user_id: string;
  im_union_id: string | null;
  im_display_name: string | null;
  bound_via: "code" | "oauth_auto" | "admin" | string;
  bound_at: string;
  last_seen_at: string | null;
}

export interface BindingCode {
  code: string;
  provider: string | null;
  expires_at: string;
  ttl_seconds: number;
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

export async function listMyBindings(
  fetchImpl: typeof fetch = fetch,
): Promise<ImBinding[]> {
  const res = await fetchImpl("/api/v1/me/bindings", {
    credentials: "include",
  });
  return readEnvelope<ImBinding[]>(res);
}

export async function createBindingCode(
  provider: ImBindingProvider | null,
  fetchImpl: typeof fetch = fetch,
): Promise<BindingCode> {
  const res = await fetchImpl("/api/v1/me/binding-codes", {
    method: "POST",
    credentials: "include",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(provider ? { provider } : {}),
  });
  return readEnvelope<BindingCode>(res);
}

export async function deleteBinding(
  bindingId: number,
  fetchImpl: typeof fetch = fetch,
): Promise<void> {
  const res = await fetchImpl(`/api/v1/me/bindings/${bindingId}`, {
    method: "DELETE",
    credentials: "include",
  });
  await readEnvelope<null>(res);
}
