"use client";
import Link from "next/link";
import { useSearchParams, useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { loginSchema } from "@/lib/validation";
import { z } from "zod";
import { Button, Field, inputClass } from "@/components/ui";
import { safeReturnTo } from "@/lib/auth/cookies";
type Values = z.infer<typeof loginSchema>;
export default function Login() {
  const router = useRouter(),
    params = useSearchParams();
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<Values>({ resolver: zodResolver(loginSchema) });
  async function submit(values: Values) {
    const r = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(values),
    });
    if (!r.ok) {
      setError("root", {
        message:
          r.status === 401
            ? "Email or password is incorrect."
            : "Login is unavailable. Please try again.",
      });
      return;
    }
    router.replace(safeReturnTo(params.get("returnTo")));
  }
  return (
    <main className="grid min-h-screen lg:grid-cols-2">
      <section className="hidden bg-emerald-950 p-16 text-white lg:flex lg:flex-col lg:justify-between">
        <div className="text-2xl font-black">studyEase</div>
        <div>
          <p className="text-sm font-bold uppercase tracking-widest text-lime-300">
            Learn with evidence
          </p>
          <h1 className="mt-4 max-w-xl text-5xl font-black leading-tight">
            Turn courses and your own notes into lasting understanding.
          </h1>
          <p className="mt-5 max-w-lg text-emerald-100">
            Adaptive practice, thoughtful schedules, and answers grounded in
            sources you can inspect.
          </p>
        </div>
        <p className="text-sm text-emerald-200">
          Your work stays scoped to your account and enrolled courses.
        </p>
      </section>
      <section className="grid place-items-center p-6">
        <form
          className="card w-full max-w-md p-7 md:p-9"
          onSubmit={handleSubmit(submit)}
          noValidate
        >
          <h1 className="text-3xl font-black">Welcome back</h1>
          <p className="mt-2 text-slate-600">Sign in to continue learning.</p>
          {params.get("reason") === "expired" && (
            <p
              role="status"
              className="mt-4 rounded-xl bg-amber-50 p-3 text-sm text-amber-900"
            >
              Your session expired. Please sign in again.
            </p>
          )}
          {errors.root && (
            <p
              role="alert"
              className="mt-4 rounded-xl bg-red-50 p-3 text-sm text-red-800"
            >
              {errors.root.message}
            </p>
          )}
          <div className="mt-6 grid gap-4">
            <Field label="Email" error={errors.email?.message}>
              <input
                className={inputClass}
                autoComplete="email"
                type="email"
                {...register("email")}
              />
            </Field>
            <Field label="Password" error={errors.password?.message}>
              <input
                className={inputClass}
                autoComplete="current-password"
                type="password"
                {...register("password")}
              />
            </Field>
            <Button disabled={isSubmitting} type="submit">
              {isSubmitting ? "Signing in…" : "Sign in"}
            </Button>
          </div>
          <p className="mt-5 text-center text-sm">
            New to studyEase?{" "}
            <Link
              className="font-bold text-emerald-800 underline"
              href="/register"
            >
              Create an account
            </Link>
          </p>
        </form>
      </section>
    </main>
  );
}
