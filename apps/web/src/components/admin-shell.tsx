import Image from "next/image";
import Link from "next/link";
import { PanelLeft, UserRound } from "lucide-react";
import "./admin-shell.css";

/* The shell adapts the AdminCN Free sidebar/header/inset/footer layout.
 * See THIRD_PARTY_ADMINCN_LICENSE.md for the upstream MIT notice. */
export function AdminShell({ locale, children }: { locale: "en" | "ta"; children: React.ReactNode }) {
  const labels = locale === "ta"
    ? { skip: "உள்ளடக்கத்திற்குச் செல்", workspace: "நிர்வாகப் பணியிடம்", modules: "பணியிடங்கள்", account: "என் கணக்கு" }
    : { skip: "Skip to content", workspace: "Administration", modules: "Workspaces", account: "My account" };

  return <div className="edp-admin-shell">
    <a className="edp-admin-skip" href="#admin-content">{labels.skip}</a>
    <aside className="edp-admin-sidebar" aria-label={labels.workspace}>
      <div className="edp-admin-brand">
        <Image src="/cse-logo.png" width={38} height={38} alt="" />
        <span><strong>CSJE</strong><small>{labels.workspace}</small></span>
      </div>
      <div className="edp-admin-sidebar-label">{labels.modules}</div>
    </aside>
    <div className="edp-admin-inset">
      <header className="edp-admin-header">
        <div className="edp-admin-header-title"><PanelLeft size={19} aria-hidden="true" /><span>{labels.workspace}</span></div>
        <Link className="edp-admin-account" href={`/${locale}/account`}><UserRound size={17} aria-hidden="true" />{labels.account}</Link>
      </header>
      <div className="edp-admin-content" id="admin-content" tabIndex={-1}>{children}</div>
      <footer className="edp-admin-footer"><span>CSJE</span><span>Admin UI: <a href="https://shadcnstudio.com/">shadcn/studio</a></span></footer>
    </div>
  </div>;
}
