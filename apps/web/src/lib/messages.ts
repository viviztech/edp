export const messages = {
  en: {
    organization: "Center for Social Justice and Equity",
    title: "Entrepreneurship Development Program",
    introduction: "Build your skills. Shape your business.",
    description: "Learning, mentoring and practical support for your entrepreneurial journey.",
    availability: "Program details and applications will be available here soon.",
    language: "தமிழில் படிக்க", skip: "Skip to content", home: "Home", navigation: "Public navigation", apply: "Explore applications", discoverEyebrow: "Start here", discoverTitle: "Find your place in the program",
    staff: "Staff access", staffMessage: "Staff sign-in will be available when account access opens.",
    loading: "Loading…", error: "This page could not load. Please try again.", retry: "Try again",
  },
  ta: {
    organization: "சமூக நீதி மற்றும் சமத்துவ மையம்",
    title: "தொழில்முனைவோர் மேம்பாட்டுத் திட்டம்",
    introduction: "திறன்களை வளர்த்திடுங்கள். தொழிலை உருவாக்குங்கள்.",
    description: "உங்கள் தொழில்முனைவுப் பயணத்திற்கான கற்றல், வழிகாட்டுதல் மற்றும் நடைமுறை ஆதரவு.",
    availability: "திட்ட விவரங்களும் விண்ணப்பங்களும் விரைவில் இங்கே கிடைக்கும்.",
    language: "Read in English", skip: "உள்ளடக்கத்திற்குச் செல்க", home: "முகப்பு", navigation: "\u0baa\u0bca\u0ba4\u0bc1 \u0bb5\u0bb4\u0bbf\u0b95\u0bbe\u0b9f\u0bcd\u0b9f\u0bbf", apply: "\u0bb5\u0bbf\u0ba3\u0bcd\u0ba3\u0baa\u0bcd\u0baa\u0bae\u0bcd", discoverEyebrow: "\u0b87\u0b99\u0bcd\u0b95\u0bc7 \u0ba4\u0bca\u0b9f\u0b99\u0bcd\u0b95\u0bb5\u0bc1\u0bae\u0bcd", discoverTitle: "\u0ba4\u0bbf\u0b9f\u0bcd\u0b9f\u0ba4\u0bcd\u0ba4\u0bbf\u0bb2\u0bcd \u0b89\u0b99\u0bcd\u0b95\u0bb3\u0bcd \u0b87\u0b9f\u0ba4\u0bcd\u0ba4\u0bc8\u0b95\u0bcd \u0b95\u0ba3\u0bcd\u0b9f\u0bc1\u0b95\u0bca\u0bb3\u0bcd\u0bb3\u0bb5\u0bc1\u0bae\u0bcd",
    staff: "பணியாளர் அணுகல்", staffMessage: "கணக்கு அணுகல் திறக்கப்பட்டதும் பணியாளர் உள்நுழைவு கிடைக்கும்.",
    loading: "ஏற்றப்படுகிறது…", error: "இந்தப் பக்கத்தை ஏற்ற முடியவில்லை. மீண்டும் முயலவும்.", retry: "மீண்டும் முயல்க",
  },
} as const;
export type Locale = keyof typeof messages;
export function isLocale(value: string): value is Locale { return value === "en" || value === "ta"; }
