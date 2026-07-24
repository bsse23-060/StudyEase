"use client";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import { qk } from "@/lib/query-keys";
import type { User } from "@/lib/api/types";
export function useSession() {
  return useQuery({
    queryKey: qk.me,
    queryFn: () => api<User>(endpoints.me),
    retry: false,
    staleTime: 60_000,
  });
}
