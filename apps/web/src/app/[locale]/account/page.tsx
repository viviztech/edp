import { notFound } from "next/navigation";
import { authMessages } from "../../../lib/auth-messages";
import { isLocale } from "../../../lib/messages";
import Account from "./view";
import Link from "next/link";
import { publicLaunch, launchCopy } from "../../../lib/public-launch";

export const metadata = { robots: { index: false, follow: false } };
export const dynamic = "force-dynamic";

export default async function AccountPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();
  const launch = publicLaunch();
  return (
    <main id="main" className="account-shell">
      {!launch.selfService && (
        <div className="launch-account-note">
          <p>{launchCopy[locale].registration}</p>
          {launch.demo && (
            <Link className="public-text-link" href={`/${locale}/demo`}>
              {launchCopy[locale].demo}
            </Link>
          )}
        </div>
      )}
      <Account
        text={authMessages[locale]}
        locale={locale}
        selfServiceEnabled={launch.selfService}
      />
    </main>
  );
}
