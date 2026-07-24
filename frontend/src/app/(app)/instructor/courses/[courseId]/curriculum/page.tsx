import { redirect } from "next/navigation";
export default async function Curriculum({
  params,
}: {
  params: Promise<{ courseId: string }>;
}) {
  redirect(`/instructor/builder?course=${(await params).courseId}`);
}
