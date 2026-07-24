"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  BookOpen,
  Bot,
  CalendarDays,
  FileText,
  Gauge,
  GraduationCap,
  Library,
  LogOut,
  Map,
  Menu,
  Settings2,
  UserRound,
  X,
} from "lucide-react";
import { useState } from "react";
import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useSession } from "@/hooks/use-session";
import { Button, Skeleton } from "./ui";
const student = [
  ["Dashboard", "/dashboard", Gauge],
  ["Explore courses", "/courses", Library],
  ["My courses", "/learn", GraduationCap],
  ["Roadmap", "/roadmap", Map],
  ["Flashcards", "/flashcards", BookOpen],
  ["Study schedule", "/schedule", CalendarDays],
  ["Documents", "/documents", FileText],
  ["Study assistant", "/assistant", Bot],
] as const;
const instructor = [
  ["Dashboard", "/dashboard", Gauge],
  ["My courses", "/instructor/courses", GraduationCap],
  ["Course builder", "/instructor/builder", Settings2],
  ["Students", "/instructor/students", UserRound],
  ["Documents", "/documents", FileText],
  ["Retrieval preview", "/instructor/retrieval", Bot],
] as const;
export function AppShell({ children }: { children: React.ReactNode }) {
  const { data: user, isLoading } = useSession();
  const pathname = usePathname();
  const router = useRouter();
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  useEffect(() => {
    if (!isLoading && !user)
      router.replace(`/login?returnTo=${encodeURIComponent(pathname)}`);
  }, [isLoading, pathname, router, user]);
  if (isLoading)
    return (
      <main className="mx-auto max-w-5xl p-8">
        <Skeleton />
      </main>
    );
  if (!user) return null;
  const nav = user.role === "student" ? student : instructor;
  async function logout() {
    await fetch("/api/auth/logout", { method: "POST" });
    qc.clear();
    router.replace("/login?reason=logout");
  }
  return (
    <div className="min-h-screen md:grid md:grid-cols-[260px_1fr]">
      <aside className="relative hidden border-r border-slate-200 bg-white p-5 md:block">
        <Brand />
        <nav aria-label="Primary" className="mt-8 grid gap-1">
          {nav.map(([label, href, Icon]) => (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-3 rounded-xl px-3 py-2.5 ${pathname.startsWith(href) ? "bg-emerald-50 font-bold text-emerald-900" : "text-slate-600 hover:bg-slate-50"}`}
            >
              <Icon size={19} />
              {label}
            </Link>
          ))}
        </nav>
        <UserCard user={user.full_name} role={user.role} logout={logout} />
      </aside>
      <div>
        <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-slate-200 bg-[var(--paper)]/95 px-4 backdrop-blur md:px-8">
          <button
            className="md:hidden"
            onClick={() => setOpen(true)}
            aria-label="Open navigation"
          >
            <Menu />
          </button>
          <div className="md:hidden">
            <Brand />
          </div>
          <Link
            href="/profile"
            className="rounded-full bg-white px-3 py-2 text-sm font-semibold"
          >
            {user.full_name}
          </Link>
        </header>
        {open && (
          <div className="fixed inset-0 z-50 bg-black/30 md:hidden">
            <aside className="h-full w-[85%] max-w-xs bg-white p-5">
              <div className="flex justify-between">
                <Brand />
                <button
                  onClick={() => setOpen(false)}
                  aria-label="Close navigation"
                >
                  <X />
                </button>
              </div>
              <nav className="mt-8 grid gap-1">
                {nav.map(([label, href, Icon]) => (
                  <Link
                    onClick={() => setOpen(false)}
                    key={href}
                    href={href}
                    className="flex items-center gap-3 rounded-xl px-3 py-3"
                  >
                    <Icon size={19} />
                    {label}
                  </Link>
                ))}
              </nav>
            </aside>
          </div>
        )}
        <main id="main-content" className="mx-auto max-w-7xl p-4 md:p-8">
          {children}
        </main>
      </div>
    </div>
  );
}
function Brand() {
  return (
    <Link
      href="/dashboard"
      className="flex items-center gap-2 text-xl font-black"
    >
      <span className="grid h-9 w-9 place-items-center rounded-xl bg-emerald-800 text-lime-200">
        sE
      </span>
      studyEase
    </Link>
  );
}
function UserCard({
  user,
  role,
  logout,
}: {
  user: string;
  role: string;
  logout: () => void;
}) {
  return (
    <div className="absolute bottom-5 left-5 right-5 rounded-xl bg-slate-50 p-3">
      <p className="truncate font-bold">{user}</p>
      <p className="mb-2 text-xs capitalize text-slate-500">{role}</p>
      <Button className="w-full" variant="secondary" onClick={logout}>
        <LogOut className="mr-2" size={16} />
        Log out
      </Button>
    </div>
  );
}
