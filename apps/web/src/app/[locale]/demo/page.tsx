import { notFound } from "next/navigation";
import { DemoExperience } from "../../../components/demo-experience";
import { isLocale } from "../../../lib/messages";
import { publicLaunch } from "../../../lib/public-launch";

export const metadata = {
  title: "CSJE EDP · Interactive demo",
  robots: { index: false, follow: false },
};
export const dynamic = "force-dynamic";

export default async function DemoPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  if (!isLocale(locale) || !publicLaunch().demo) notFound();
  return (
    <main id="main" className="demo-main">
      <DemoExperience locale={locale} />
    </main>
  );
}
