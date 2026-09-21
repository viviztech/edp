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
