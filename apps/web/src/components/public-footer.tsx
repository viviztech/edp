import Image from "next/image";
import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { messages, type Locale } from "../lib/messages";
import { publicNavLabels, starterPageList } from "../lib/public-site-content";
import { launchCopy, publicLaunch } from "../lib/public-launch";

export function PublicFooter({ locale }: { locale: Locale }) {
  const text = messages[locale];
  const labels = publicNavLabels[locale];
  const pages = starterPageList(locale);
  const launch = publicLaunch();
  const copy =
    locale === "en"
      ? {
          intro:
            "Opening pathways to learning, entrepreneurship, and a future with more possibilities.",
          connect: "Stay connected",
          account: "Your account",
          line: "Learn. Connect. Build.",
          rights: "Center for Social Justice and Equity",
        }
      : {
          intro:
            "கற்றல், தொழில்முனைவு மற்றும் அதிக வாய்ப்புகளுடன் கூடிய எதிர்காலத்திற்கான பாதைகள்.",
          connect: "தொடர்பில் இருங்கள்",
          account: "உங்கள் கணக்கு",
          line: "கற்போம். இணைவோம். உருவாக்குவோம்.",
          rights: "சமூக நீதி மற்றும் சமத்துவ மையம்",
        };
  return (
    <footer className="site-footer">
      <div className="site-footer-inner">
        <div className="footer-intro">
          <Link className="footer-brand" href={`/${locale}`}>
            <Image src="/cse-logo.png" width={64} height={64} alt="" />
            <span>
              <strong>CSJE</strong>
              <small>{text.organization}</small>
            </span>
          </Link>
          <p>{copy.intro}</p>
          <span className="footer-tagline">
            {copy.line}
            <ArrowUpRight size={18} aria-hidden="true" />
          </span>
        </div>
        <div className="footer-links">
          <h2>{labels.program}</h2>
          {pages
            .filter((page) => page.group === "program")
            .slice(0, 4)
            .map((page) => (
              <Link key={page.slug} href={`/${locale}/pages/${page.slug}`}>
                {page.title}
              </Link>
            ))}
        </div>
        <div className="footer-links">
          <h2>{labels.support}</h2>
          <Link href={`/${locale}/tools/idea-planner`}>
            {launchCopy[locale].planner}
          </Link>
          {pages
            .filter((page) => page.group === "support")
            .slice(0, 4)
            .map((page) => (
              <Link key={page.slug} href={`/${locale}/pages/${page.slug}`}>
                {page.title}
              </Link>
            ))}
        </div>
        <div className="footer-links">
          <h2>{copy.connect}</h2>
          <Link href={`/${locale}/pages/contact`}>{labels.contact}</Link>
          <Link href={`/${locale}/content/faq`}>{labels.faq}</Link>
          <Link href={`/${locale}/pages/privacy`}>
            {launchCopy[locale].privacy}
          </Link>
          {launch.demo && (
            <Link href={`/${locale}/demo`}>{launchCopy[locale].demo}</Link>
          )}
          <Link href={`/${locale}/account`}>
            {launch.selfService ? copy.account : launchCopy[locale].signIn}
          </Link>
          <Link
            href={`/${locale === "en" ? "ta" : "en"}`}
            lang={locale === "en" ? "ta" : "en"}
          >
            {text.language}
          </Link>
        </div>
      </div>
      <div className="footer-bottom">
        <span>
          © {new Date().getFullYear()} {copy.rights}
        </span>
        <span>{text.title}</span>
      </div>
    </footer>
  );
}
