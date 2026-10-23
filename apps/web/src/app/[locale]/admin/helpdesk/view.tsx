"use client";
import HelpdeskWorkspace from "../../helpdesk/view";
import type { Locale } from "../../helpdesk/content";
export default function HelpdeskStaff(props: { org: string; locale: Locale; userId: string; permissions: string[] }) {
  return <HelpdeskWorkspace {...props} staff />;
}
