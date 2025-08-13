"use client";
import { useHydratedAuth } from "@/hooks/useHydratedAuth";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

export function useModGuard() {
  const { user, isAuthenticated, isHydrated } = useHydratedAuth();
  const router = useRouter();

  const ready = isHydrated;
  const isMod = !!user && ["moderator", "superadmin"].includes(user.role?.name || "");

  return { user, isAuthenticated, ready, isMod: ["moderator", "superadmin"].includes(user?.role?.name || "") };
}
