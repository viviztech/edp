"use client";

import { useSelectedLayoutSegment } from "next/navigation";
import type { ReactNode } from "react";

/** The locale layout is shared by public and staff routes. */
export function PublicRouteChrome({
  header,
  footer,
  children,
}: {
  header: ReactNode;
  footer: ReactNode;
  children: ReactNode;
}) {
  const isAdmin = useSelectedLayoutSegment() === "admin";
  return <>{!isAdmin && header}{children}{!isAdmin && footer}</>;
}
