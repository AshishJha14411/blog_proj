"use client";
import { useHydratedAuth } from "@/hooks/useHydratedAuth";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

export function useModGuard() {
  const { user, isAuthenticated, isHydrated } = useHydratedAuth();
  const router = useRouter();

  const ready = isHydrated;
  const isMod = !!user && ["moderator", "superadmin"].includes(user.role?.name || "");

  // Redirect non-mods once hydration has resolved; otherwise the page would
  // just render blank because the guard only *returned* a flag.
  useEffect(() => {
    if (ready && !isMod) {
      router.replace("/");
    }
  }, [ready, isMod, router]);

  return { user, isAuthenticated, ready, isMod };
}
