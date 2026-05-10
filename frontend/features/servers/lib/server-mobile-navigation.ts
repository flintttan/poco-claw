import type { WorkspaceMode } from "@/features/servers/ui/server-workspace-types";

export function shouldShowServerMobileDetail({
  isDesktop,
  channelId,
  modeFromUrl,
}: {
  isDesktop: boolean;
  channelId?: string | null;
  modeFromUrl?: WorkspaceMode | null;
}) {
  if (isDesktop) {
    return true;
  }
  return Boolean(channelId || modeFromUrl);
}
