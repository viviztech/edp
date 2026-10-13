import type { Locale } from "./messages";

export function publicLaunch() {
  const email = process.env.PUBLIC_CONTACT_EMAIL?.trim() || "";
  const phone = process.env.PUBLIC_CONTACT_PHONE?.trim() || "";
  const whatsapp =
    process.env.PUBLIC_CONTACT_WHATSAPP?.replace(/\D/g, "") || "";
  return {
    demo: process.env.PUBLIC_DEMO_ENABLED === "true",
    selfService: process.env.PUBLIC_SELF_SERVICE_ENABLED === "true",
    email: /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) ? email : "",
    phone: /^[+\d ()-]{7,32}$/.test(phone) ? phone : "",
    whatsapp: /^\d{8,15}$/.test(whatsapp) ? whatsapp : "",
  };
}

export const launchCopy = {
  en: {
    action: "Get in touch",
    signIn: "Sign in",
    faq: "FAQs",
    privacy: "Privacy",
    planner: "Idea planner",
    demo: "Try the demo",
    available:
      "Start with an idea. Explore the program and build your first plan today.",
    contactIntro:
      "Tell us where you are in your entrepreneurship journey and what you would like to know.",
    registration:
      "Program applications are handled through the program team. Get in touch to discuss participation; this sign-in is for existing accounts.",
    resourceTitle: "Put your idea on paper.",
    resourceIntro:
      "A simple worksheet to turn a thought into a clearer plan. No account needed, and your answers stay in this browser tab.",
    resourceAction: "Open the idea planner",
    email: "Email the team",
    phone: "Call the team",
    whatsapp: "Chat on WhatsApp",
  },
  ta: {
    action: "தொடர்பு கொள்ளுங்கள்",
    signIn: "உள்நுழைக",
    faq: "கேள்வி பதில்கள்",
    privacy: "தனியுரிமை",
    planner: "யோசனைத் திட்டமிடல்",
    demo: "செயல்விளக்கத்தை முயலுங்கள்",
    available:
      "ஒரு யோசனையுடன் தொடங்குங்கள். திட்டத்தை அறிந்து உங்கள் முதல் திட்டத்தை இன்றே உருவாக்குங்கள்.",
    contactIntro:
      "உங்கள் தொழில்முனைவுப் பயணத்தில் நீங்கள் எங்கே இருக்கிறீர்கள், என்ன தெரிந்துகொள்ள விரும்புகிறீர்கள் என்பதைப் பகிருங்கள்.",
    registration:
      "திட்டத்தில் பங்கேற்பது குறித்து திட்டக் குழுவைத் தொடர்பு கொள்ளுங்கள். இந்த உள்நுழைவு ஏற்கனவே கணக்கு உள்ளவர்களுக்கானது.",
    resourceTitle: "உங்கள் யோசனைக்கு வடிவம் கொடுங்கள்.",
    resourceIntro:
      "ஒரு யோசனையைத் தெளிவான திட்டமாக மாற்ற எளிய பயிற்சித்தாள். கணக்கு தேவையில்லை. உங்கள் பதில்கள் இந்த உலாவித் தாவலிலேயே இருக்கும்.",
    resourceAction: "யோசனைத் திட்டமிடலைத் திறக்கவும்",
    email: "மின்னஞ்சல் அனுப்புங்கள்",
    phone: "அழைக்கவும்",
    whatsapp: "வாட்ஸ்அப்பில் பேசுங்கள்",
  },
} satisfies Record<Locale, Record<string, string>>;
