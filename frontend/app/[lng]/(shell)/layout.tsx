import { redirect } from "next/navigation";

import { AppShell } from "@/components/shell/app-shell";
import {
  buildHomePath,
  buildLoginPath,
  buildSessionRecoveryPath,
} from "@/features/auth";
import { getServerAuthState } from "@/features/auth/lib/server-session";

export default async function ShellLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ lng: string }>;
}) {
  const { lng } = await params;
  const authState = await getServerAuthState();

  if (authState.status === "anonymous") {
    redirect(buildLoginPath(lng, buildHomePath(lng)));
  }
  if (authState.status === "stale") {
    redirect(buildSessionRecoveryPath(lng, buildHomePath(lng)));
  }

  return <AppShell lng={lng}>{children}</AppShell>;
}
