import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowRight, ArrowUpRight, BookOpen, Compass, Lightbulb, Sprout } from "lucide-react";
import { isLocale, messages } from "../../lib/messages";
import { starterPageList } from "../../lib/public-site-content";

const homeCopy = {
  en: {
    label: "Entrepreneurship Development Program",
    headline: "An idea is a beginning. Build what comes next.",
    intro: "A guided path for people exploring entrepreneurship—from learning the essentials to shaping a business plan and finding support along the way.",
    journeyLink: "Explore the journey", applicationLink: "Explore applications",
    heroFrom: "START WITH AN IDEA", heroTo: "BUILD TOWARD IMPACT", statusLabel: "Program update",
    journeyEyebrow: "The journey", journeyTitle: "Every venture starts somewhere.",
    journeyIntro: "The program is designed to bring the steps of entrepreneurship into one connected experience.",
    steps: [
      { title: "Discover", body: "Learn about the program, understand eligibility, and see where your interests might lead." },
      { title: "Apply", body: "Create an account, share your idea, and follow your application as it progresses." },
      { title: "Learn & connect", body: "Build practical skills through training, resources, and guidance from mentors." },
      { title: "Plan & grow", body: "Develop a business plan and explore relevant opportunities for the next stage." },
    ],
    supportEyebrow: "More than a course", supportTitle: "Support for the whole path, not just the first step.",
    supportBody: "The EDP platform brings program information, learning, mentoring, business planning, and post-training support together in one place. Availability of each service depends on the program stage.",
    supportItems: [
      { title: "Practical learning", body: "Training and resources connected to the work of starting a business." },
      { title: "Guidance along the way", body: "Mentoring and program support as ideas become plans." },
      { title: "A view of what’s next", body: "Space to explore schemes, funding, and opportunities as they are published." },
    ],
    discoverEyebrow: "Explore", discoverTitle: "Find the information you need.",
    discoverBody: "Explore the essentials, then browse all pages for more detail and current updates.",
    allPages: "View all public pages",
    emptyPages: "Program pages are being prepared. Check back for eligibility, benefits, training details, and resources.",
    closeEyebrow: "Your next step", closeTitle: "Ready to explore your possibility?",
    closeBody: "Start with the program information, then visit your account to explore applications when you are ready.",
  },
  ta: {
    label: "தொழில்முனைவோர் மேம்பாட்டுத் திட்டம்",
    headline: "ஒரு யோசனைதான் தொடக்கம். அடுத்த படியை உருவாக்குங்கள்.",
    intro: "தொழில்முனைவை ஆராய்பவர்களுக்கான வழிகாட்டப்பட்ட பாதை—அடிப்படைகளைக் கற்றுக்கொள்வதிலிருந்து தொழில் திட்டத்தை உருவாக்கி, தேவையான ஆதரவை அறிந்துகொள்வது வரை.",
    journeyLink: "பயணத்தை அறிக", applicationLink: "விண்ணப்பங்களைப் பார்க்க",
    heroFrom: "யோசனையுடன் தொடங்குங்கள்", heroTo: "மாற்றத்தை நோக்கி வளருங்கள்", statusLabel: "திட்ட அறிவிப்பு",
    journeyEyebrow: "உங்கள் பயணம்", journeyTitle: "ஒவ்வொரு தொழிலும் ஓர் இடத்தில் தொடங்குகிறது.",
    journeyIntro: "தொழில்முனைவின் படிகளை ஒரே தொடர்ச்சியான அனுபவமாக இணைக்கும் வகையில் இந்தத் திட்டம் வடிவமைக்கப்பட்டுள்ளது.",
    steps: [
      { title: "அறிந்துகொள்ளுங்கள்", body: "திட்டம், தகுதி, உங்கள் ஆர்வத்திற்கு ஏற்ற வாய்ப்புகள் ஆகியவற்றைப் பற்றி அறிக." },
      { title: "விண்ணப்பியுங்கள்", body: "கணக்கை உருவாக்கி, உங்கள் யோசனையைப் பகிர்ந்து, விண்ணப்பத்தின் முன்னேற்றத்தைப் பாருங்கள்." },
      { title: "கற்றுக் கொள்ளுங்கள்", body: "பயிற்சி, வளங்கள், வழிகாட்டிகளின் உதவியுடன் நடைமுறைத் திறன்களை வளர்த்துக் கொள்ளுங்கள்." },
      { title: "திட்டமிட்டு வளருங்கள்", body: "தொழில் திட்டத்தை உருவாக்கி, அடுத்த கட்டத்திற்கான வாய்ப்புகளை ஆராயுங்கள்." },
    ],
    supportEyebrow: "பயிற்சியைத் தாண்டி", supportTitle: "தொடக்கம் முதல் வளர்ச்சி வரை துணை.",
    supportBody: "திட்டத் தகவல்கள், கற்றல், வழிகாட்டுதல், தொழில் திட்டமிடல், பயிற்சிக்குப் பிந்தைய ஆதரவு ஆகியவற்றை EDP தளம் ஒரே இடத்தில் இணைக்கிறது. ஒவ்வொரு சேவையும் திட்டத்தின் கட்டத்தைப் பொறுத்து கிடைக்கும்.",
    supportItems: [
      { title: "நடைமுறை கற்றல்", body: "தொழில் தொடங்குவதற்கான பயிற்சியும் அதனுடன் தொடர்புடைய வளங்களும்." },
      { title: "பயணத்தில் வழிகாட்டுதல்", body: "யோசனைகளைத் திட்டங்களாக்க உதவும் வழிகாட்டுதலும் திட்ட ஆதரவும்." },
      { title: "அடுத்த வாய்ப்புகள்", body: "வெளியிடப்படும் திட்டங்கள், நிதி வாய்ப்புகள், பிற வாய்ப்புகளை ஆராயும் இடம்." },
    ],
    discoverEyebrow: "ஆராயுங்கள்", discoverTitle: "உங்களுக்குத் தேவையான தகவலைக் கண்டறியுங்கள்.",
    discoverBody: "அடிப்படைத் தகவல்களை ஆராய்ந்து, மேலும் விவரங்களுக்கும் தற்போதைய செய்திகளுக்கும் அனைத்து பக்கங்களையும் பாருங்கள்.",
    allPages: "அனைத்து பொதுப் பக்கங்களும்",
    emptyPages: "திட்டப் பக்கங்கள் தயாராகின்றன. தகுதி, நன்மைகள், பயிற்சி விவரங்கள் மற்றும் வளங்களுக்காக மீண்டும் பாருங்கள்.",
    closeEyebrow: "அடுத்த படி", closeTitle: "உங்கள் வாய்ப்பை ஆராயத் தயாரா?",
    closeBody: "திட்டத் தகவல்களுடன் தொடங்குங்கள். தயாரானதும் உங்கள் கணக்கில் விண்ணப்பங்களைப் பாருங்கள்.",
  },
} as const;

const stepIcons = [Compass, Lightbulb, BookOpen, Sprout];

export async function generateMetadata({ params }: { params: Promise<{ locale: string }> }): Promise<Metadata> {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();
  return {
    title: messages[locale].title,
    description: messages[locale].description,
    openGraph: {
      title: messages[locale].title,
      description: messages[locale].description,
      images: [{ url: "/cse-logo.png", width: 900, height: 900, alt: "Social Justice Entrepreneurs Hub logo" }],
    },
  };
}

export default async function Home({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  if (!isLocale(locale)) notFound();
  const copy = homeCopy[locale];
  const text = messages[locale];
  const navigation = starterPageList(locale).filter((page) =>
    ["about", "eligibility", "benefits", "training-structure", "resources", "apply"].includes(page.slug));

  return <main id="main" className="landing-main">
    <section className="landing-hero" aria-labelledby="home-title">
      <div className="landing-hero-copy">
        <p className="landing-kicker"><span aria-hidden="true" />{copy.label}</p>
        <h1 id="home-title">{copy.headline}</h1>
        <p className="landing-lead">{copy.intro}</p>
        <div className="landing-actions">
          <a className="landing-button landing-button-primary" href="#journey">{copy.journeyLink}<ArrowRight size={18} aria-hidden="true" /></a>
          <Link className="landing-button landing-button-text" href={"/" + locale + "/account"}>{copy.applicationLink}<ArrowUpRight size={17} aria-hidden="true" /></Link>
        </div>
      </div>
      <div className="landing-hero-visual" aria-hidden="true">
        <div className="landing-visual-grid" />
        <div className="landing-orbit landing-orbit-one" />
        <div className="landing-orbit landing-orbit-two" />
        <div className="landing-visual-label landing-visual-label-top"><span>01</span>{copy.heroFrom}</div>
        <div className="landing-visual-center"><Image src="/cse-logo.png" width={180} height={180} alt="" priority /></div>
        <div className="landing-visual-label landing-visual-label-bottom"><span>04</span>{copy.heroTo}</div>
      </div>
    </section>

    <div className="landing-status" role="status"><span className="landing-status-mark" aria-hidden="true" /><strong>{copy.statusLabel}</strong><span>{text.availability}</span></div>

    <section id="journey" className="landing-section landing-journey" aria-labelledby="journey-title">
      <div className="landing-section-heading"><p className="landing-kicker">{copy.journeyEyebrow}</p><h2 id="journey-title">{copy.journeyTitle}</h2><p>{copy.journeyIntro}</p></div>
      <ol className="landing-steps">{copy.steps.map((step, index) => { const Icon = stepIcons[index]; return <li key={step.title}><div className="landing-step-top"><span>{String(index + 1).padStart(2, "0")}</span><Icon size={22} strokeWidth={1.6} aria-hidden="true" /></div><h3>{step.title}</h3><p>{step.body}</p></li>; })}</ol>
    </section>

    <section className="landing-support" aria-labelledby="support-title">
      <div className="landing-support-intro"><p className="landing-kicker">{copy.supportEyebrow}</p><h2 id="support-title">{copy.supportTitle}</h2><p>{copy.supportBody}</p></div>
      <div className="landing-support-list">{copy.supportItems.map((item, index) => <div className="landing-support-item" key={item.title}><span>{String(index + 1).padStart(2, "0")}</span><div><h3>{item.title}</h3><p>{item.body}</p></div></div>)}</div>
    </section>

    <section className="landing-section landing-discover" aria-labelledby="discover-title">
      <div className="landing-section-heading"><p className="landing-kicker">{copy.discoverEyebrow}</p><h2 id="discover-title">{copy.discoverTitle}</h2><p>{copy.discoverBody}</p></div>
      <div className="landing-page-grid">{navigation.map((page, index) => <Link className="landing-page-link" key={page.slug} href={"/" + locale + "/pages/" + page.slug}><span className="landing-page-index">{String(index + 1).padStart(2, "0")}</span><strong>{page.title}</strong><ArrowUpRight size={21} aria-hidden="true" /></Link>)}</div>
      <Link className="landing-all-pages" href={"/" + locale + "/pages"}>{copy.allPages}<ArrowRight size={18} aria-hidden="true" /></Link>
    </section>

    <section className="landing-close" aria-labelledby="close-title"><div><p className="landing-kicker">{copy.closeEyebrow}</p><h2 id="close-title">{copy.closeTitle}</h2><p>{copy.closeBody}</p></div><Link className="landing-button landing-button-primary" href={"/" + locale + "/account"}>{copy.applicationLink}<ArrowRight size={18} aria-hidden="true" /></Link></section>
  </main>;
}
