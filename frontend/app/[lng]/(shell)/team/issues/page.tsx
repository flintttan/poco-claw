import { redirect } from "next/navigation";

export default async function TeamIssuesPage({
  params,
}: {
  params: Promise<{ lng: string }>;
}) {
  const { lng } = await params;
  redirect(`/${lng}/servers`);
}
