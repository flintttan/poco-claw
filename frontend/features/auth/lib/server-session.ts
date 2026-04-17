import "server-only";

import { cache } from "react";
import { cookies } from "next/headers";

import { ApiError } from "@/lib/errors";
import { API_ENDPOINTS, apiClient } from "@/services/api-client";
import { AUTH_SESSION_COOKIE_NAME } from "@/features/auth/lib/paths";

export type ServerAuthState =
  | { status: "anonymous" }
  | { status: "authenticated" }
  | { status: "stale" };

export const getServerAuthState = cache(async (): Promise<ServerAuthState> => {
  const cookieStore = await cookies();
  if (!cookieStore.get(AUTH_SESSION_COOKIE_NAME)?.value) {
    return { status: "anonymous" };
  }

  try {
    await apiClient.get<unknown>(API_ENDPOINTS.authMe, {
      cache: "no-store",
    });
    return { status: "authenticated" };
  } catch (error) {
    if (error instanceof ApiError && error.statusCode === 401) {
      return { status: "stale" };
    }
    throw error;
  }
});
