import { ServerConversationPageClient } from "@/features/servers/ui/server-conversation-page-client";

export default async function ServerChannelPage({
  params,
}: {
  params: Promise<{ serverId: string; channelId: string }>;
}) {
  const { serverId, channelId } = await params;
  return (
    <ServerConversationPageClient serverId={serverId} channelId={channelId} />
  );
}
