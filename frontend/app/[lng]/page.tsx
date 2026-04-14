import { redirect } from "next/navigation";

import {
  buildHomePath,
  buildLoginPath,
  buildSessionRecoveryPath,
} from "@/features/auth";
import { getServerAuthState } from "@/features/auth/lib/server-session";

export default async function Page({
  params,
}: {
  params: Promise<{ lng: string }>;
}) {
  const { lng } = await params;
  const authState = await getServerAuthState();

  if (authState.status === "authenticated") {
    redirect(buildHomePath(lng));
  }
  if (authState.status === "stale") {
    redirect(buildSessionRecoveryPath(lng, buildHomePath(lng)));
  }

  redirect(buildLoginPath(lng, buildHomePath(lng)));
}
