"use client";
import { Button } from "@/components/ui";
export default function ErrorPage({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <main className="grid min-h-screen place-items-center p-6">
      <div className="card max-w-lg p-8 text-center">
        <h1 className="text-2xl font-bold">This page could not load</h1>
        <p className="mt-2 text-slate-600">
          Check your connection, then try again.
        </p>
        <Button className="mt-5" onClick={reset}>
          Try again
        </Button>
      </div>
    </main>
  );
}
