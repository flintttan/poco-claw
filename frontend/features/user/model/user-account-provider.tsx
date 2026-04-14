"use client";

import * as React from "react";
import { usePathname, useRouter } from "next/navigation";

import { ApiError } from "@/lib/errors";
import { buildHomePath, buildSessionRecoveryPath } from "@/features/auth";
import { userService } from "@/features/user/api/user-api";
import type { UserCredits, UserProfile } from "@/features/user/types";

interface UserAccountContextValue {
  profile: UserProfile | null;
  credits: UserCredits | null;
  isLoading: boolean;
  refresh: () => Promise<void>;
  logout: () => Promise<void>;
}

const UserAccountContext = React.createContext<UserAccountContextValue | null>(
  null,
);

interface UserAccountProviderProps {
  lng: string;
  children: React.ReactNode;
}

export function UserAccountProvider({
  lng,
  children,
}: UserAccountProviderProps) {
  const router = useRouter();
  const pathname = usePathname();
  const [profile, setProfile] = React.useState<UserProfile | null>(null);
  const [credits, setCredits] = React.useState<UserCredits | null>(null);
  const [isLoading, setIsLoading] = React.useState(true);

  const redirectToSessionRecovery = React.useCallback(
    (nextPath: string) => {
      setProfile(null);
      setCredits(null);
      router.replace(buildSessionRecoveryPath(lng, nextPath));
    },
    [lng, router],
  );

  const refresh = React.useCallback(async () => {
    setIsLoading(true);
    try {
      const [nextProfile, nextCredits] = await Promise.all([
        userService.getProfile(),
        userService.getCredits(),
      ]);
      if (nextProfile === null) {
        redirectToSessionRecovery(pathname || buildHomePath(lng));
        return;
      }
      setProfile(nextProfile);
      setCredits(nextCredits);
    } catch (error) {
      if (error instanceof ApiError && error.statusCode === 401) {
        redirectToSessionRecovery(pathname || buildHomePath(lng));
      } else {
        console.error("Failed to load current user", error);
      }
    } finally {
      setIsLoading(false);
    }
  }, [pathname, redirectToSessionRecovery, lng]);

  React.useEffect(() => {
    void refresh();
  }, [refresh]);

  const logout = React.useCallback(async () => {
    redirectToSessionRecovery(buildHomePath(lng));
  }, [lng, redirectToSessionRecovery]);

  const value = React.useMemo(
    () => ({ profile, credits, isLoading, refresh, logout }),
    [credits, isLoading, logout, profile, refresh],
  );

  return (
    <UserAccountContext.Provider value={value}>
      {children}
    </UserAccountContext.Provider>
  );
}

export function useUserAccountContext(): UserAccountContextValue {
  const context = React.useContext(UserAccountContext);
  if (context === null) {
    throw new Error("useUserAccount must be used within UserAccountProvider");
  }
  return context;
}
