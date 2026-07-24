"use client";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api, json } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import { useSession } from "@/hooks/use-session";
import { PageHeading } from "@/components/page-heading";
import { Button, Field, Skeleton, inputClass, useToast } from "@/components/ui";
import { useState } from "react";
export default function Profile() {
  const { data: user, isLoading } = useSession(),
    qc = useQueryClient();
  if (isLoading) return <Skeleton />;
  if (!user) return null;
  return <ProfileForm key={user.id} user={user} qc={qc} />;
}
function ProfileForm({
  user,
  qc,
}: {
  user: import("@/lib/api/types").User;
  qc: ReturnType<typeof useQueryClient>;
}) {
  const toast = useToast();
  const [form, setForm] = useState({
    full_name: user.full_name,
    goal: user.goal,
    weekly_hours: user.weekly_hours,
    language_preference: user.language_preference,
  });
  const save = useMutation({
    mutationFn: () => api(endpoints.me, { method: "PATCH", ...json(form) }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["me"] });
      toast("Profile updated.");
    },
  });
  return (
    <>
      <PageHeading
        eyebrow="Account"
        title="Profile and preferences"
        description={`Signed in as ${user?.email}. Your role (${user?.role}) can only be changed by an administrator.`}
      />
      <form
        className="card grid max-w-2xl gap-4 p-6"
        onSubmit={(e) => {
          e.preventDefault();
          save.mutate();
        }}
      >
        <Field label="Full name">
          <input
            className={inputClass}
            value={form.full_name}
            onChange={(e) =>
              setForm((f) => ({ ...f, full_name: e.target.value }))
            }
          />
        </Field>
        <Field label="Learning goal">
          <input
            className={inputClass}
            value={form.goal}
            onChange={(e) => setForm((f) => ({ ...f, goal: e.target.value }))}
          />
        </Field>
        <Field label="Weekly study hours">
          <input
            className={inputClass}
            type="number"
            min="0"
            value={form.weekly_hours}
            onChange={(e) =>
              setForm((f) => ({ ...f, weekly_hours: Number(e.target.value) }))
            }
          />
        </Field>
        <Field label="Language preference">
          <input
            className={inputClass}
            value={form.language_preference}
            onChange={(e) =>
              setForm((f) => ({ ...f, language_preference: e.target.value }))
            }
          />
        </Field>
        <Button className="justify-self-start" disabled={save.isPending}>
          Save changes
        </Button>
      </form>
    </>
  );
}
