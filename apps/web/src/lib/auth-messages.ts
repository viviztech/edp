export const authMessages = {
  en: {
    title: "Your account", email: "Email", password: "Password", name: "Name", token: "Verification or reset code",
    login: "Sign in", register: "Create account", verify: "Verify email", requestVerification: "Send verification",
    requestReset: "Forgot password", reset: "Reset password", logout: "Sign out", logoutAll: "Sign out all devices",
    accepted: "If the account is eligible, a message has been queued. Follow the instructions in that message.",
    completed: "Done. You can now sign in.", loading: "Please wait…", error: "The request could not be completed. Check your details and try again.",
    unavailable: "Account messages are not available yet. Please try again later.", invalid: "Email or password is incorrect, or the account is not verified.",
    limited: "Too many attempts. Please wait 15 minutes.", sessionExpired: "Your session expired. Please sign in again.",
    sessions: "Active devices", noSessions: "No active devices.", revoke: "Sign out device", current: "This device",
    staff: "Staff workspace", denied: "You do not have access to this workspace.", organizations: "Your organizations",
    audit: "Audit history", noAudit: "No audit events to show.", passwordHelp: "Use 12–128 characters.", back: "Back to account",
    noOrganizations: "No staff access is assigned to your account.", refresh: "Refresh", next: "Next"
  },
  ta: {
    title: "உங்கள் கணக்கு", email: "மின்னஞ்சல்", password: "கடவுச்சொல்", name: "பெயர்", token: "சரிபார்ப்பு அல்லது மீட்டமைப்புக் குறியீடு",
    login: "உள்நுழைக", register: "கணக்கை உருவாக்குக", verify: "மின்னஞ்சலைச் சரிபார்க்க", requestVerification: "சரிபார்ப்பை அனுப்புக",
    requestReset: "கடவுச்சொல் மறந்துவிட்டதா", reset: "கடவுச்சொல்லை மீட்டமைக்க", logout: "வெளியேறுக", logoutAll: "எல்லாச் சாதனங்களிலிருந்தும் வெளியேறுக",
    accepted: "கணக்கு தகுதியுடையதாக இருந்தால், செய்தி வரிசையில் சேர்க்கப்பட்டுள்ளது. அந்தச் செய்தியின் வழிமுறைகளைப் பின்பற்றவும்.",
    completed: "முடிந்தது. இப்போது உள்நுழையலாம்.", loading: "காத்திருக்கவும்…", error: "கோரிக்கையை நிறைவேற்ற முடியவில்லை. விவரங்களைச் சரிபார்த்து மீண்டும் முயலவும்.",
    unavailable: "கணக்குச் செய்திகள் இன்னும் கிடைக்கவில்லை. பின்னர் முயலவும்.", invalid: "மின்னஞ்சல் அல்லது கடவுச்சொல் தவறு, அல்லது கணக்கு சரிபார்க்கப்படவில்லை.",
    limited: "அதிக முயற்சிகள். 15 நிமிடங்கள் காத்திருக்கவும்.", sessionExpired: "அமர்வு காலாவதியானது. மீண்டும் உள்நுழைக.",
    sessions: "செயலில் உள்ள சாதனங்கள்", noSessions: "செயலில் சாதனங்கள் இல்லை.", revoke: "சாதனத்திலிருந்து வெளியேறுக", current: "இந்தச் சாதனம்",
    staff: "பணியாளர் பணியிடம்", denied: "இந்தப் பணியிடத்திற்கான அணுகல் உங்களிடம் இல்லை.", organizations: "உங்கள் நிறுவனங்கள்",
    audit: "தணிக்கை வரலாறு", noAudit: "தணிக்கை நிகழ்வுகள் இல்லை.", passwordHelp: "12–128 எழுத்துகளைப் பயன்படுத்துக.", back: "கணக்கிற்குத் திரும்புக",
    noOrganizations: "உங்கள் கணக்கிற்குப் பணியாளர் அணுகல் வழங்கப்படவில்லை.", refresh: "புதுப்பிக்க", next: "அடுத்து"
  }
} as const;
export type AuthMessages = { [K in keyof typeof authMessages.en]: string };
