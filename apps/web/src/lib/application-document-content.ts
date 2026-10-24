export const applicationDocumentWords = {
  en: {
    title: "Application documents", noRequirements: "This form has no document requirements.",
    configuredOnly: "Configure only approved requirements. Publishing this form does not enable file collection.",
    add: "Add document requirement", remove: "Remove requirement", key: "Stable document key",
    labelEn: "English document label", labelTa: "Tamil document label",
    instructionsEn: "English instructions", instructionsTa: "Tamil instructions",
    policy: "Published file policy edition", choose: "Choose explicitly", savedPolicy: "Saved policy edition",
    minimum: "Minimum files", maximum: "Maximum files", countHelp: "Enter both counts explicitly. Zero minimum makes this requirement optional. The policy also limits the total across requirements.",
    noPolicies: "No published application-document policy is loaded. Create and publish explicit policy rules before assigning one.",
    policyError: "Policy editions could not be loaded. Your entered requirements are preserved.",
    policyDenied: "Viewing file policies is required to configure document requirements.",
    morePolicies: "Load more policy editions", reloadPolicies: "Reload policy editions",
    edition: "Edition", moveUp: "Move requirement up", moveDown: "Move requirement down",
    formats: "Allowed formats", maxBytes: "Maximum bytes per file", policyMaximum: "Policy maximum files",
    retention: "Retention days", rejectedRetention: "Rejected-file retention days",
    disabled: "File collection is disabled. These configured requirements do not provide upload access.",
    notice: "File policy notice", upload: "Upload document", replace: "Replace document", removeDocument: "Remove document",
    selectFile: "Choose a file", send: "Upload selected file", refresh: "Refresh document status",
    invalidFile: "Choose a nonempty file in an allowed format and within the displayed size limit.",
    saveFirst: "Save your application answers before changing documents. Your entered answers are preserved.",
    scanning: "Checks are pending. Only verified clean files can be submitted.",
    saved: "Document change saved.", uncertain: "The document change could not be confirmed. Refresh its saved status before another command. Do not resend the upload automatically.",
    failed: "Document information could not be loaded. Your application answers are preserved.",
    cleanRequired: "Complete the document requirements with verified clean files before submitting.",
    frozen: "Submitted document evidence is read-only.", digest: "SHA-256", bytes: "Bytes", version: "File version",
    more: "Load more documents", recoverCreate: "Recover the same document registration", continueUpload: "Continue this registered upload",
    reviewSaved: "Read current document", removeConfirm: "Remove this document from the draft? Its stored bytes remain subject to the file policy.",
    cancel: "Cancel file selection", changed: "The application version changed. Reload and review the saved application before changing documents.",
    uploadLimit: "Current upload limit (bytes)", count: "Files", minimumRequired: "Minimum required", maximumAllowed: "Maximum allowed",
    reselect: "Choose a replacement file before uploading. Replacement creates a new document identity.", downloading: "Download verified document",
    readOnly: "Documents are read-only for this application.", working: "Please wait…",
    assignedDocuments: "Read assigned application documents", noDocuments: "No active documents are recorded.",
    unavailable: "This evidence is unavailable under the current retention or file rules.",
    states: { pending: "Awaiting upload", uploading: "Uploading", quarantined: "Awaiting scan", scanning: "Scanning", clean: "Verified clean", infected: "Unsafe file", rejected: "Rejected", deleted: "Disposed" },
  },
  ta: {
    title: "விண்ணப்ப ஆவணங்கள்", noRequirements: "இந்தப் படிவத்தில் ஆவணத் தேவைகள் இல்லை.",
    configuredOnly: "அங்கீகரிக்கப்பட்ட தேவைகளை மட்டும் அமைக்கவும். படிவத்தை வெளியிடுவது கோப்பு சேகரிப்பைத் தொடங்காது.",
    add: "ஆவணத் தேவையைச் சேர்", remove: "தேவையை நீக்கு", key: "நிலையான ஆவணக் குறியீடு",
    labelEn: "ஆங்கில ஆவணப் பெயர்", labelTa: "தமிழ் ஆவணப் பெயர்",
    instructionsEn: "ஆங்கில வழிமுறைகள்", instructionsTa: "தமிழ் வழிமுறைகள்",
    policy: "வெளியிடப்பட்ட கோப்புக் கொள்கைப் பதிப்பு", choose: "வெளிப்படையாகத் தேர்ந்தெடுக்கவும்", savedPolicy: "சேமிக்கப்பட்ட கொள்கைப் பதிப்பு",
    minimum: "குறைந்தபட்ச கோப்புகள்", maximum: "அதிகபட்ச கோப்புகள்", countHelp: "இரு எண்ணிக்கைகளையும் உள்ளிடவும். குறைந்தபட்சம் பூஜ்ஜியம் எனில் இந்தத் தேவை விருப்பமானது. அனைத்துத் தேவைகளின் மொத்தத்தையும் கொள்கை கட்டுப்படுத்தும்.",
    noPolicies: "வெளியிடப்பட்ட விண்ணப்ப ஆவணக் கொள்கை ஏற்றப்படவில்லை. ஒன்றைத் தேர்ந்தெடுக்க முன் வெளிப்படையான விதிகளை உருவாக்கி வெளியிடவும்.",
    policyError: "கொள்கைப் பதிப்புகளை ஏற்ற முடியவில்லை. உள்ளிட்ட தேவைகள் பாதுகாக்கப்பட்டுள்ளன.",
    policyDenied: "ஆவணத் தேவைகளை அமைக்க கோப்புக் கொள்கைகளைப் பார்க்கும் அனுமதி தேவை.",
    morePolicies: "மேலும் கொள்கைப் பதிப்புகளை ஏற்று", reloadPolicies: "கொள்கைப் பதிப்புகளை மீண்டும் ஏற்று",
    edition: "பதிப்பு", moveUp: "தேவையை மேலே நகர்த்து", moveDown: "தேவையை கீழே நகர்த்து",
    formats: "அனுமதிக்கப்பட்ட வடிவங்கள்", maxBytes: "ஒரு கோப்பின் அதிகபட்ச பைட்டுகள்", policyMaximum: "கொள்கையின் அதிகபட்ச கோப்புகள்",
    retention: "தக்கவைப்பு நாட்கள்", rejectedRetention: "நிராகரிக்கப்பட்ட கோப்பின் தக்கவைப்பு நாட்கள்",
    disabled: "கோப்பு சேகரிப்பு முடக்கப்பட்டுள்ளது. அமைக்கப்பட்ட தேவைகள் பதிவேற்ற அனுமதியை வழங்காது.",
    notice: "கோப்புக் கொள்கை அறிவிப்பு", upload: "ஆவணத்தைப் பதிவேற்று", replace: "ஆவணத்தை மாற்று", removeDocument: "ஆவணத்தை நீக்கு",
    selectFile: "ஒரு கோப்பைத் தேர்ந்தெடு", send: "தேர்ந்தெடுத்த கோப்பைப் பதிவேற்று", refresh: "ஆவண நிலையைப் புதுப்பி",
    invalidFile: "அனுமதிக்கப்பட்ட வடிவத்திலும் காட்டப்பட்ட அளவிற்குள்ளும் உள்ள காலியாகாத கோப்பைத் தேர்ந்தெடுக்கவும்.",
    saveFirst: "ஆவணங்களை மாற்றும் முன் விண்ணப்பப் பதில்களைச் சேமிக்கவும். உள்ளிட்ட பதில்கள் பாதுகாக்கப்பட்டுள்ளன.",
    scanning: "சோதனைகள் நிலுவையில் உள்ளன. சரிபார்க்கப்பட்ட பாதுகாப்பான கோப்புகளை மட்டுமே சமர்ப்பிக்கலாம்.",
    saved: "ஆவண மாற்றம் சேமிக்கப்பட்டது.", uncertain: "ஆவண மாற்றத்தை உறுதிப்படுத்த முடியவில்லை. மற்றொரு கட்டளைக்கு முன் சேமிக்கப்பட்ட நிலையைப் புதுப்பிக்கவும். தானாக மீண்டும் பதிவேற்ற வேண்டாம்.",
    failed: "ஆவணத் தகவலை ஏற்ற முடியவில்லை. விண்ணப்பப் பதில்கள் பாதுகாக்கப்பட்டுள்ளன.",
    cleanRequired: "சமர்ப்பிக்கும் முன் சரிபார்க்கப்பட்ட பாதுகாப்பான கோப்புகளுடன் ஆவணத் தேவைகளை நிறைவு செய்யவும்.",
    frozen: "சமர்ப்பிக்கப்பட்ட ஆவணச் சான்றுகளை மாற்ற முடியாது.", digest: "SHA-256", bytes: "பைட்டுகள்", version: "கோப்புப் பதிப்பு",
    more: "மேலும் ஆவணங்களை ஏற்று", recoverCreate: "அதே ஆவணப் பதிவை மீட்டெடு", continueUpload: "இந்தப் பதிவு செய்யப்பட்ட பதிவேற்றத்தைத் தொடர்க",
    reviewSaved: "தற்போதைய ஆவணத்தைப் படி", removeConfirm: "வரைவிலிருந்து இந்த ஆவணத்தை நீக்கவா? சேமிக்கப்பட்ட பைட்டுகளுக்கு கோப்புக் கொள்கை தொடர்ந்து பொருந்தும்.",
    cancel: "கோப்புத் தேர்வை ரத்து செய்", changed: "விண்ணப்பப் பதிப்பு மாறியுள்ளது. ஆவணங்களை மாற்ற முன் சேமிக்கப்பட்ட விண்ணப்பத்தை மீண்டும் ஏற்றி பரிசீலிக்கவும்.",
    uploadLimit: "தற்போதைய பதிவேற்ற வரம்பு (பைட்டுகள்)", count: "கோப்புகள்", minimumRequired: "தேவையான குறைந்தபட்சம்", maximumAllowed: "அனுமதிக்கப்பட்ட அதிகபட்சம்",
    reselect: "பதிவேற்ற முன் மாற்றுக் கோப்பைத் தேர்ந்தெடுக்கவும். மாற்றுவது புதிய ஆவண அடையாளத்தை உருவாக்கும்.", downloading: "சரிபார்க்கப்பட்ட ஆவணத்தைப் பதிவிறக்கு",
    readOnly: "இந்த விண்ணப்பத்தின் ஆவணங்களைப் பார்க்க மட்டுமே முடியும்.", working: "காத்திருக்கவும்…",
    assignedDocuments: "ஒதுக்கப்பட்ட விண்ணப்ப ஆவணங்களைப் படி", noDocuments: "நடப்பில் உள்ள ஆவணங்கள் பதிவாகவில்லை.",
    unavailable: "தற்போதைய தக்கவைப்பு அல்லது கோப்பு விதிகளின்படி இந்தச் சான்று கிடைக்கவில்லை.",
    states: { pending: "பதிவேற்றம் நிலுவை", uploading: "பதிவேற்றப்படுகிறது", quarantined: "சோதனை நிலுவை", scanning: "சோதிக்கப்படுகிறது", clean: "சரிபார்க்கப்பட்ட பாதுகாப்பான கோப்பு", infected: "பாதுகாப்பற்ற கோப்பு", rejected: "நிராகரிக்கப்பட்டது", deleted: "அழிக்கப்பட்டது" },
  },
} as const;

export type DraftDocumentRequirement = {
  key: string; label_en: string; label_ta: string; instructions_en: string; instructions_ta: string;
  file_policy_id: string; min_files: string; max_files: string;
};
export const newDocumentRequirement = (key: string): DraftDocumentRequirement => ({
  key, label_en: "", label_ta: "", instructions_en: "", instructions_ta: "",
  file_policy_id: "", min_files: "", max_files: "",
});
export function serializeDocumentRequirements(values: DraftDocumentRequirement[]) {
  if (values.length > 20 || new Set(values.map(value => value.key.trim())).size !== values.length
    || values.some(value => !/^[a-z][a-z0-9_]{0,79}$/.test(value.key.trim())
    || !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value.file_policy_id)
    || [value.label_en, value.label_ta].some(text => !text.trim() || text.trim().length > 200)
    || [value.instructions_en, value.instructions_ta].some(text => !text.trim() || text.trim().length > 2000)
    || !/^(?:0|[1-9][0-9]?|100)$/.test(value.min_files)
    || !/^(?:[1-9][0-9]?|100)$/.test(value.max_files) || Number(value.min_files) > Number(value.max_files))) return null;
  return values.map(value => ({ ...value, key: value.key.trim(), label_en: value.label_en.trim(), label_ta: value.label_ta.trim(),
    instructions_en: value.instructions_en.trim(), instructions_ta: value.instructions_ta.trim(),
    min_files: Number(value.min_files), max_files: Number(value.max_files) }));
}
