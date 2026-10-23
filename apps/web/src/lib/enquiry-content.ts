import type { components } from "./api-contracts";
export type EnquiryPolicy = components["schemas"]["EnquiryPolicy"];
export type Enquiry = components["schemas"]["EnquiryView"];
export type EnquiryList = components["schemas"]["EnquiryList"];

export const enquiryWords = {
  en: {
    title: "Send an enquiry", name: "Name", email: "Email", phone: "Phone (optional)", message: "Your enquiry",
    privacy: "Read the privacy notice", send: "Send enquiry", sending: "Sending…", reload: "Reload page",
    unavailable: "The enquiry form is not available yet. Please check the published contact information or try again later.",
    error: "Your enquiry could not be confirmed. Your details are preserved; please try again.",
    invalid: "Check the required fields and your consent before sending.",
    changed: "The privacy notice changed. Reload this page and review the current notice before sending.",
    limited: "Too many requests. Please wait before trying again.",
    accepted: "Your enquiry was accepted.", reference: "Reference", website: "Leave this field empty",
    workspace: "Enquiry inbox", queue: "Enquiries", details: "Enquiry details", empty: "No enquiries match this filter.",
    all: "All statuses", new: "New", reviewed: "Reviewed", closed: "Closed", status: "Status", refresh: "Refresh",
    more: "Load more", loading: "Loading…", saved: "Saved.", consentVersion: "Consent version", received: "Received",
    markReviewed: "Mark reviewed", close: "Close enquiry", conflict: "This enquiry changed. Refresh its details before making another change.",
    staffError: "The enquiry could not be loaded or saved. Refresh to recover.",
    uncertain: "The change could not be confirmed. Refresh the enquiry before trying again.",
    refreshed: "Details refreshed. Review the current record before saving.", denied: "You do not have access to this enquiry workspace.",
    choose: "Select an enquiry to see its details.",
  },
  ta: {
    title: "விசாரணை அனுப்பவும்", name: "பெயர்", email: "மின்னஞ்சல்", phone: "தொலைபேசி (விருப்பம்)", message: "உங்கள் விசாரணை",
    privacy: "தனியுரிமை அறிவிப்பைப் படிக்கவும்", send: "விசாரணை அனுப்பு", sending: "அனுப்பப்படுகிறது…", reload: "பக்கத்தை மீண்டும் ஏற்று",
    unavailable: "விசாரணைப் படிவம் இன்னும் கிடைக்கவில்லை. வெளியிடப்பட்ட தொடர்புத் தகவலைப் பார்க்கவும் அல்லது பின்னர் முயற்சிக்கவும்.",
    error: "உங்கள் விசாரணையை உறுதிப்படுத்த முடியவில்லை. உங்கள் தகவல் உள்ளது; மீண்டும் முயற்சிக்கவும்.",
    invalid: "தேவையான விவரங்களையும் ஒப்புதலையும் சரிபார்க்கவும்.",
    changed: "தனியுரிமை அறிவிப்பு மாறியுள்ளது. பக்கத்தை மீண்டும் ஏற்றி தற்போதைய அறிவிப்பைப் படிக்கவும்.",
    limited: "அதிக கோரிக்கைகள் வந்துள்ளன. சிறிது நேரம் காத்திருந்து மீண்டும் முயற்சிக்கவும்.",
    accepted: "உங்கள் விசாரணை ஏற்கப்பட்டது.", reference: "குறிப்பு எண்", website: "இந்தப் புலத்தை காலியாக விடவும்",
    workspace: "விசாரணைப் பெட்டி", queue: "விசாரணைகள்", details: "விசாரணை விவரங்கள்", empty: "இந்த வடிகட்டியில் விசாரணைகள் இல்லை.",
    all: "அனைத்து நிலைகளும்", new: "புதியது", reviewed: "பார்வையிட்டது", closed: "முடிக்கப்பட்டது", status: "நிலை", refresh: "புதுப்பிக்கவும்",
    more: "மேலும் ஏற்றவும்", loading: "ஏற்றப்படுகிறது…", saved: "சேமிக்கப்பட்டது.", consentVersion: "ஒப்புதல் பதிப்பு", received: "பெறப்பட்டது",
    markReviewed: "பார்வையிட்டதாகக் குறி", close: "விசாரணையை முடிக்கவும்", conflict: "விசாரணை மாறியுள்ளது. மீண்டும் மாற்றுவதற்கு முன் விவரங்களைப் புதுப்பிக்கவும்.",
    staffError: "விசாரணையை ஏற்றவோ சேமிக்கவோ முடியவில்லை. புதுப்பித்து மீட்கவும்.",
    uncertain: "மாற்றத்தை உறுதிப்படுத்த முடியவில்லை. முதலில் விவரங்களைப் புதுப்பிக்கவும்.",
    refreshed: "விவரங்கள் புதுப்பிக்கப்பட்டன. சேமிப்பதற்கு முன் சரிபார்க்கவும்.", denied: "இந்த விசாரணைப் பகுதிக்கான அனுமதி உங்களுக்கு இல்லை.",
    choose: "விவரங்களைப் பார்க்க ஒரு விசாரணையைத் தேர்ந்தெடுக்கவும்.",
  },
} as const;
