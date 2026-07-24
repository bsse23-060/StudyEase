import { redirect } from "next/navigation";
export default async function Documents({
  params,
}: {
  params: Promise<{ courseId: string }>;
}) {
  redirect(`/documents?course=${(await params).courseId}`);
}
