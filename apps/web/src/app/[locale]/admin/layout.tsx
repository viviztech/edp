import { notFound } from "next/navigation";
import { AdminShell } from "../../../components/admin-shell";
import { isLocale } from "../../../lib/messages";
import "./workspaces.css";

export const metadata = { robots: { index: false, follow: false } };

export default async function AdminLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();
  return <AdminShell locale={locale}>{children}</AdminShell>;
}
