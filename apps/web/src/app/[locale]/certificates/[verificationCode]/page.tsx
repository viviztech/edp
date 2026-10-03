import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";
import type { components } from "../../../../lib/api-contracts";
import { learningMessages } from "../../../../lib/learning-messages";
import { isLocale } from "../../../../lib/messages";
import { serverApi } from "../../../../lib/server-api";

type Certificate = components["schemas"]["PublicCertificateView"];

export const metadata = { robots: { index: false, follow: false } };

export default async function CertificateVerificationPage({
  params,
}: {
  params: Promise<{ locale: string; verificationCode: string }>;
}) {
  const { locale, verificationCode } = await params;
  if (!isLocale(locale) || !/^[A-Za-z0-9_-]{20,48}$/.test(verificationCode)) notFound();
  const text = learningMessages[locale];
  let response: Response;
  try {
    response = await serverApi(`/certificates/verify/${verificationCode}`);
  } catch {
    response = new Response(null, { status: 503 });
  }
  if (response.status === 404) notFound();
  if (!response.ok) {
    return <main className="learning-main"><h1>{text.verifyCertificate}</h1>
      <p>{text.error}</p></main>;
  }
  const certificate = await response.json() as Certificate;
  const value = (en: string, ta: string) => locale === "ta" ? ta : en;
  return <main className="learning-main certificate-verification">
    <article className="certificate-card">
      <Image
        alt={text.certificateQr}
        height="180"
        src={`/api/certificates/verify/${verificationCode}/qr`}
        unoptimized
        width="180"
      />
      <div>
        <p className="eyebrow">{text.verifiedCertificate}</p>
        <h1>{value(certificate.certificate_title_en, certificate.certificate_title_ta)}</h1>
        <h2>{value(certificate.course_title_en, certificate.course_title_ta)}</h2>
        <p>{certificate.issuer_name}</p>
        <p>{text.issuedOn}: {new Intl.DateTimeFormat(locale, { dateStyle: "long" })
          .format(new Date(certificate.issued_at))}</p>
        <strong>{text.certificateStatus}: {certificate.status === "valid"
          ? text.validCertificate : text.revokedCertificate}</strong>
        <small>{text.verificationCode}: {certificate.verification_code}</small>
      </div>
    </article>
    <Link href={`/${locale}`}>{text.backHome}</Link>
  </main>;
}
