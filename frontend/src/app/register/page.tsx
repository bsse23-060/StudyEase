"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { registerSchema } from "@/lib/validation";
import { z } from "zod";
import { Button, Field, inputClass } from "@/components/ui";
type Values = z.infer<typeof registerSchema>;
export default function Register() {
  const router = useRouter();
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<Values>({
    resolver: zodResolver(registerSchema),
    defaultValues: { level_preference: "college" },
  });
  async function submit(values: Values) {
    const r = await fetch("/api/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(values),
    });
    if (!r.ok) {
      const b = await r.json();
      Object.entries(b).forEach(([k, v]) =>
        setError(k as keyof Values, {
          message: Array.isArray(v) ? String(v[0]) : String(v),
        }),
      );
      return;
    }
    const login = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: values.email, password: values.password }),
    });
    router.replace(login.ok ? "/dashboard" : "/login");
  }
  return (
    <main className="grid min-h-screen place-items-center p-6">
      <form
        className="card w-full max-w-lg p-7"
        onSubmit={handleSubmit(submit)}
        noValidate
      >
        <h1 className="text-3xl font-black">Create your learning space</h1>
        <p className="mt-2 text-slate-600">
          New accounts are students. Staff roles are assigned by an
          administrator.
        </p>
        <div className="mt-6 grid gap-4">
          <Field label="Full name" error={errors.full_name?.message}>
            <input
              className={inputClass}
              autoComplete="name"
              {...register("full_name")}
            />
          </Field>
          <Field label="Email" error={errors.email?.message}>
            <input
              className={inputClass}
              type="email"
              autoComplete="email"
              {...register("email")}
            />
          </Field>
          <Field
            label="Password"
            hint="Use at least 8 characters."
            error={errors.password?.message}
          >
            <input
              className={inputClass}
              type="password"
              autoComplete="new-password"
              {...register("password")}
            />
          </Field>
          <Field
            label="Learning level"
            error={errors.level_preference?.message}
          >
            <select className={inputClass} {...register("level_preference")}>
              <option value="school">School</option>
              <option value="college">College</option>
              <option value="professional">Professional</option>
            </select>
          </Field>
          <Button disabled={isSubmitting}>
            {isSubmitting ? "Creating account…" : "Create account"}
          </Button>
        </div>
        <p className="mt-5 text-center text-sm">
          <Link className="font-bold text-emerald-800 underline" href="/login">
            Back to sign in
          </Link>
        </p>
      </form>
    </main>
  );
}
