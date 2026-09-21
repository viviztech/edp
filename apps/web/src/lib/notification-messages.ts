export const notificationMessages = {
  en: {
    workspace: "Notifications", description: "Lead assignments and follow-up reminders for your organization.",
    back: "Back to staff home", error: "Could not load notifications. Refresh and try again.",
    conflict: "This changed while you were viewing it. Refresh and try again.",
    loading: "Working…", preference: "Lead assignment notices", enabled: "On", disabled: "Off",
    enable: "Turn on", disable: "Turn off", leadAssigned: "A lead was assigned to you",
    followupPreference: "Follow-up reminders", followupDue: "A CRM follow-up is due",
    openCrm: "Open CRM queue", markRead: "Mark as read", read: "Read", unread: "Unread",
    empty: "No notifications yet.", more: "Load more", refresh: "Refresh",
    updated: "Preference saved.", marked: "Notification marked read.", permission: "You do not have access to this inbox.",
  },
  ta: {
    workspace: "அறிவிப்புகள்", description: "உங்கள் நிறுவனத்தின் முன்னணி ஒதுக்கீட்டு அறிவிப்புகள்.",
    back: "பணியாளர் முகப்புக்கு", error: "அறிவிப்புகளை ஏற்ற முடியவில்லை. புதுப்பித்து மீண்டும் முயலவும்.",
    conflict: "இந்தப் பதிவு மாறியுள்ளது. புதுப்பித்து மீண்டும் முயலவும்.",
    loading: "செயல்படுகிறது…", preference: "முன்னணி ஒதுக்கீட்டு அறிவிப்புகள்", enabled: "இயக்கு", disabled: "நிறுத்து",
    enable: "இயக்கு", disable: "நிறுத்து", leadAssigned: "ஒரு முன்னணி உங்களுக்கு ஒதுக்கப்பட்டது",
    followupPreference: "பின்தொடர்பு நினைவூட்டல்கள்", followupDue: "CRM பின்தொடர்புக்கான நேரம் வந்துள்ளது",
    openCrm: "CRM வரிசையைத் திற", markRead: "படித்ததாகக் குறி", read: "படித்தது", unread: "படிக்காதது",
    empty: "இன்னும் அறிவிப்புகள் இல்லை.", more: "மேலும் காட்டு", refresh: "புதுப்பி",
    updated: "விருப்பம் சேமிக்கப்பட்டது.", marked: "அறிவிப்பு படித்ததாகக் குறிக்கப்பட்டது.", permission: "இந்த அறிவிப்புகளை அணுக அனுமதி இல்லை.",
  },
} as const;
export type NotificationLocale = keyof typeof notificationMessages;
