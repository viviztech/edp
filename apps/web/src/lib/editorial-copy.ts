import type { EditorialKind } from "./public-editorial";
import type { Locale } from "./messages";

export const editorialLabels: Record<Locale, Record<EditorialKind, string>> = {
  en: { news: "News", event: "Events", faq: "Frequently asked questions", testimonial: "Stories" },
  ta: {
    news: "\u0b9a\u0bc6\u0baf\u0bcd\u0ba4\u0bbf\u0b95\u0bb3\u0bcd",
    event: "\u0ba8\u0bbf\u0b95\u0bb4\u0bcd\u0bb5\u0bc1\u0b95\u0bb3\u0bcd",
    faq: "\u0b85\u0b9f\u0bbf\u0b95\u0bcd\u0b95\u0b9f\u0bbf \u0b95\u0bc7\u0b9f\u0bcd\u0b95\u0baa\u0bcd\u0baa\u0b9f\u0bc1\u0bae\u0bcd \u0b95\u0bc7\u0bb3\u0bcd\u0bb5\u0bbf\u0b95\u0bb3\u0bcd",
    testimonial: "\u0b85\u0ba9\u0bc1\u0baa\u0bb5\u0b95\u0bcd \u0b95\u0bc1\u0bb1\u0bbf\u0baa\u0bcd\u0baa\u0bc1\u0b95\u0bb3\u0bcd",
  },
};
export const editorialEmpty: Record<Locale, string> = {
  en: "No published content yet.",
  ta: "\u0bb5\u0bc6\u0bb3\u0bbf\u0baf\u0bbf\u0b9f\u0baa\u0bcd\u0baa\u0b9f\u0bcd\u0b9f \u0b89\u0bb3\u0bcd\u0bb3\u0b9f\u0b95\u0bcd\u0b95\u0bae\u0bcd \u0b87\u0ba9\u0bcd\u0ba9\u0bc1\u0bae\u0bcd \u0b87\u0bb2\u0bcd\u0bb2\u0bc8.",
};

export const editorialIntroductions: Record<Locale, Record<EditorialKind, string>> = {
  en: {
    news: "Read program announcements and updates as they are published.",
    event: "Find upcoming public events and program activities when dates are confirmed.",
    faq: "Find answers to common questions about the program and application journey.",
    testimonial: "Read approved stories and lessons from entrepreneurship journeys.",
  },
  ta: {
    news: "வெளியிடப்படும் திட்ட அறிவிப்புகளையும் புதிய தகவல்களையும் படியுங்கள்.",
    event: "தேதிகள் உறுதி செய்யப்பட்டபின் வரவிருக்கும் பொது நிகழ்வுகளையும் திட்ட செயல்பாடுகளையும் காணுங்கள்.",
    faq: "திட்டம் மற்றும் விண்ணப்பப் பயணம் பற்றிய பொதுவான கேள்விகளுக்கான பதில்களைக் காணுங்கள்.",
    testimonial: "ஒப்புதல் பெற்ற தொழில்முனைவுப் பயணக் கதைகளையும் கற்றல்களையும் படியுங்கள்.",
  },
};
