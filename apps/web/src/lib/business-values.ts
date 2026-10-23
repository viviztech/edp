const labels = {
  en: {
    idea: "Idea", starting: "Starting", operating: "Operating", paused: "Paused", closed: "Closed",
    none: "None", seeking: "Seeking", applied: "Applied", approved: "Approved", disbursed: "Disbursed",
    under_1l: "Under ₹1 lakh", "1l_to_5l": "₹1–5 lakh", "5l_to_25l": "₹5–25 lakh", over_25l: "Over ₹25 lakh",
    under_10k: "Under ₹10,000", "10k_to_50k": "₹10,000–50,000", "50k_to_2l": "₹50,000–2 lakh", over_2l: "Over ₹2 lakh",
    undisclosed: "Prefer not to disclose", pending: "Pending", completed: "Completed",
  },
  ta: {
    idea: "யோசனை", starting: "தொடக்கம்", operating: "செயல்படுகிறது", paused: "இடைநிறுத்தம்", closed: "மூடப்பட்டது",
    none: "இல்லை", seeking: "தேடுகிறது", applied: "விண்ணப்பித்தது", approved: "ஒப்புதல் பெற்றது", disbursed: "வழங்கப்பட்டது",
    under_1l: "₹1 லட்சத்திற்குக் கீழ்", "1l_to_5l": "₹1–5 லட்சம்", "5l_to_25l": "₹5–25 லட்சம்", over_25l: "₹25 லட்சத்திற்கு மேல்",
    under_10k: "₹10,000க்குக் கீழ்", "10k_to_50k": "₹10,000–50,000", "50k_to_2l": "₹50,000–2 லட்சம்", over_2l: "₹2 லட்சத்திற்கு மேல்",
    undisclosed: "தெரிவிக்க விரும்பவில்லை", pending: "நிலுவை", completed: "முடிந்தது",
  },
} as const;

export function businessValue(locale: "en" | "ta", value: string): string {
  return value in labels[locale] ? labels[locale][value as keyof typeof labels.en] : value;
}
