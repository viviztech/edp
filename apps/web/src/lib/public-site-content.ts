import type { Locale } from "./messages";

export type StarterPage = {
  title: string;
  eyebrow: string;
  intro: string;
  sections: readonly { heading: string; body: string }[];
  note?: string;
  next?: { label: string; path: string };
};

type PageEntry = { slug: string; group: "program" | "support" | "connect"; en: StarterPage; ta: StarterPage };

export const starterPages: readonly PageEntry[] = [
  {
    slug: "about", group: "program",
    en: { title: "About the program", eyebrow: "Our purpose", intro: "The Entrepreneurship Development Program is a connected path from an early idea to practical business support. It is part of the Center for Social Justice and Equity’s digital platform.", sections: [
      { heading: "One connected journey", body: "Program discovery, applications, training, mentoring, business planning, and follow-up are designed to work together." },
      { heading: "Built around people", body: "Public visitors, applicants, participants, alumni, mentors, and program teams each have a place in the experience." },
      { heading: "A growing platform", body: "Services and information appear as they are approved and published. Check individual pages for current details." },
    ], next: { label: "Explore eligibility", path: "/pages/eligibility" } },
    ta: { title: "திட்டம் பற்றி", eyebrow: "எங்கள் நோக்கம்", intro: "தொழில்முனைவோர் மேம்பாட்டுத் திட்டம், ஆரம்ப யோசனையிலிருந்து நடைமுறை தொழில் ஆதரவு வரை இணைக்கும் பாதையாகும். இது சமூக நீதி மற்றும் சமத்துவ மையத்தின் டிஜிட்டல் தளத்தின் ஒரு பகுதியாகும்.", sections: [
      { heading: "இணைந்த பயணம்", body: "திட்ட அறிமுகம், விண்ணப்பம், பயிற்சி, வழிகாட்டுதல், தொழில் திட்டமிடல், தொடர்ந்த ஆதரவு ஆகியவை ஒன்றுடன் ஒன்று இணைக்கப்படுகின்றன." },
      { heading: "மக்களை மையமாகக் கொண்டு", body: "பொது பயனர்கள், விண்ணப்பதாரர்கள், பங்கேற்பாளர்கள், முன்னாள் மாணவர்கள், வழிகாட்டிகள், திட்டக் குழுக்கள் ஆகியோருக்கென அனுபவம் வடிவமைக்கப்படுகிறது." },
      { heading: "வளரும் தளம்", body: "ஒப்புதல் பெற்று வெளியிடப்படும் போது சேவைகளும் தகவல்களும் கிடைக்கும். தற்போதைய விவரங்களுக்கு ஒவ்வொரு பக்கத்தையும் பாருங்கள்." },
    ], next: { label: "தகுதியை அறிக", path: "/pages/eligibility" } },
  },
  {
    slug: "eligibility", group: "program",
    en: { title: "Eligibility", eyebrow: "Before you apply", intro: "Eligibility depends on the specific program and application cycle. This page is the place to review the official criteria once they are published.", sections: [
      { heading: "Review the current criteria", body: "Check the published program notice for who can apply, any required documents, and the application window." },
      { heading: "Prepare your information", body: "An application may ask about your background, interests, business idea, and supporting documents." },
      { heading: "Follow your application", body: "After submitting, use your account to see the status and any next steps that apply to you." },
    ], note: "Specific age, location, education, income, and other eligibility rules have not been published here yet.", next: { label: "How to apply", path: "/pages/apply" } },
    ta: { title: "தகுதி", eyebrow: "விண்ணப்பிக்கும் முன்", intro: "தகுதி என்பது குறிப்பிட்ட திட்டத்தையும் விண்ணப்பச் சுற்றையும் பொறுத்தது. அதிகாரப்பூர்வ நிபந்தனைகள் வெளியானதும் அவற்றை இங்கே பார்க்கலாம்.", sections: [
      { heading: "தற்போதைய நிபந்தனைகள்", body: "யார் விண்ணப்பிக்கலாம், தேவையான ஆவணங்கள், விண்ணப்பக் காலம் ஆகியவற்றை வெளியிடப்பட்ட அறிவிப்பில் சரிபாருங்கள்." },
      { heading: "தகவல்களைத் தயாரியுங்கள்", body: "உங்கள் பின்னணி, ஆர்வம், தொழில் யோசனை, ஆதார ஆவணங்கள் போன்றவை விண்ணப்பத்தில் கேட்கப்படலாம்." },
      { heading: "விண்ணப்ப நிலையைப் பாருங்கள்", body: "சமர்ப்பித்த பிறகு உங்கள் கணக்கில் நிலை மற்றும் அடுத்த படிகளைப் பார்க்கலாம்." },
    ], note: "வயது, இடம், கல்வி, வருமானம் போன்ற குறிப்பிட்ட தகுதி விதிகள் இன்னும் இங்கே வெளியிடப்படவில்லை.", next: { label: "விண்ணப்பிப்பது எப்படி", path: "/pages/apply" } },
  },
  {
    slug: "benefits", group: "program",
    en: { title: "What the program offers", eyebrow: "Benefits", intro: "The program is designed to make entrepreneurship easier to explore and plan through learning, guidance, and relevant resources.", sections: [
      { heading: "Practical learning", body: "Training can cover the fundamentals of developing an idea, understanding a market, and planning day-to-day business work." },
      { heading: "People and guidance", body: "Mentoring and program support are intended to help participants test decisions and keep moving forward." },
      { heading: "Tools for the next stage", body: "Business planning, public resources, and published opportunity information can support preparation beyond training." },
    ], note: "Participation, certificates, funding, and other outcomes depend on the applicable program rules; none is guaranteed by this page.", next: { label: "See the training structure", path: "/pages/training-structure" } },
    ta: { title: "திட்டத்தின் பயன்கள்", eyebrow: "பயன்கள்", intro: "கற்றல், வழிகாட்டுதல், தொடர்புடைய வளங்கள் மூலம் தொழில்முனைவை ஆராயவும் திட்டமிடவும் உதவும் வகையில் திட்டம் வடிவமைக்கப்பட்டுள்ளது.", sections: [
      { heading: "நடைமுறை கற்றல்", body: "யோசனையை வளர்த்தல், சந்தையைப் புரிந்துகொள்ளுதல், அன்றாட தொழில் பணிகளைத் திட்டமிடுதல் ஆகிய அடிப்படைகள் பயிற்சியில் இடம்பெறலாம்." },
      { heading: "வழிகாட்டும் மனிதர்கள்", body: "முடிவுகளைச் சோதித்துப் பார்த்து தொடர்ந்து முன்னேற வழிகாட்டுதலும் திட்ட ஆதரவும் உதவ முனைகின்றன." },
      { heading: "அடுத்த கட்டக் கருவிகள்", body: "தொழில் திட்டமிடல், பொது வளங்கள், வெளியிடப்படும் வாய்ப்புத் தகவல்கள் ஆகியவை பயிற்சிக்குப் பிந்தைய தயாரிப்புக்கு உதவலாம்." },
    ], note: "பங்கேற்பு, சான்றிதழ், நிதி மற்றும் பிற பலன்கள் தொடர்புடைய திட்ட விதிகளைப் பொறுத்தவை; இந்தப் பக்கம் அவற்றை உறுதி செய்யவில்லை.", next: { label: "பயிற்சி அமைப்பைப் பாருங்கள்", path: "/pages/training-structure" } },
  },
  {
    slug: "training-structure", group: "program",
    en: { title: "Training structure", eyebrow: "How learning works", intro: "Learning is planned as a sequence of courses, sessions, activities, and progress checks connected to the program or batch you join.", sections: [
      { heading: "Learn in stages", body: "Course modules and lessons can bring together reading, video, documents, and guided activities." },
      { heading: "Practice and feedback", body: "Assignments, quizzes, and assessments can help you apply what you learn and see where to improve." },
      { heading: "Track your progress", body: "Attendance, course progress, and certificate eligibility are managed according to the rules of your enrolled program." },
    ], note: "A detailed curriculum, timetable, center list, and certificate rules will appear when a program publishes them.", next: { label: "Explore mentoring", path: "/pages/mentors" } },
    ta: { title: "பயிற்சி அமைப்பு", eyebrow: "கற்றல் முறை", intro: "நீங்கள் சேரும் திட்டம் அல்லது குழுவுடன் இணைந்த பாடங்கள், அமர்வுகள், செயல்பாடுகள், முன்னேற்ற மதிப்பீடுகள் என கற்றல் திட்டமிடப்படுகிறது.", sections: [
      { heading: "கட்டங்களாகக் கற்றல்", body: "பாடத் தொகுதிகளும் பாடங்களும் வாசிப்பு, காணொளி, ஆவணங்கள், வழிநடத்தப்பட்ட செயல்பாடுகள் ஆகியவற்றை இணைக்கலாம்." },
      { heading: "பயிற்சியும் பின்னூட்டமும்", body: "பணிகள், வினாடி வினாக்கள், மதிப்பீடுகள் ஆகியவை கற்றதைப் பயன்படுத்தவும் மேம்படுத்த வேண்டிய இடத்தை அறியவும் உதவலாம்." },
      { heading: "முன்னேற்றத்தைப் பாருங்கள்", body: "வருகை, பாட முன்னேற்றம், சான்றிதழுக்கான தகுதி ஆகியவை சேர்ந்த திட்டத்தின் விதிகளின்படி நிர்வகிக்கப்படும்." },
    ], note: "விரிவான பாடத்திட்டம், கால அட்டவணை, மையப் பட்டியல், சான்றிதழ் விதிகள் ஆகியவை திட்டம் வெளியிடும்போது இங்கே வரும்.", next: { label: "வழிகாட்டுதலை ஆராயுங்கள்", path: "/pages/mentors" } },
  },
  {
    slug: "mentors", group: "program",
    en: { title: "Mentoring", eyebrow: "Guidance", intro: "Mentoring is intended to connect participants with relevant guidance as they develop an idea, plan a venture, and work through practical questions.", sections: [
      { heading: "Ask better questions", body: "A mentor can help you think through assumptions, challenges, and the next decision in your business plan." },
      { heading: "Keep a record", body: "The platform is designed to keep mentoring sessions, goals, and follow-up actions connected to your progress." },
      { heading: "Continue learning", body: "Guidance can sit alongside training and post-training business support when the program makes it available." },
    ], note: "Mentor names, availability, matching rules, and session schedules have not been published yet.", next: { label: "Explore resources", path: "/pages/resources" } },
    ta: { title: "வழிகாட்டுதல்", eyebrow: "ஆதரவு", intro: "யோசனையை வளர்த்தல், தொழிலைத் திட்டமிடல், நடைமுறை கேள்விகளைச் சமாளித்தல் ஆகியவற்றில் தொடர்புடைய வழிகாட்டுதலைப் பங்கேற்பாளர்களுடன் இணைப்பதே நோக்கம்.", sections: [
      { heading: "சரியான கேள்விகளைக் கேளுங்கள்", body: "தொழில் திட்டத்தில் உள்ள ஊகங்கள், சவால்கள், அடுத்த முடிவு ஆகியவற்றைப் பற்றி சிந்திக்க வழிகாட்டி உதவலாம்." },
      { heading: "பதிவை வைத்திருங்கள்", body: "வழிகாட்டல் அமர்வுகள், இலக்குகள், தொடர்ச்சி நடவடிக்கைகள் ஆகியவற்றை உங்கள் முன்னேற்றத்துடன் இணைக்க தளம் வடிவமைக்கப்படுகிறது." },
      { heading: "தொடர்ந்து கற்றுக் கொள்ளுங்கள்", body: "திட்டம் வழங்கும் போது பயிற்சியுடனும் பயிற்சிக்குப் பிந்தைய தொழில் ஆதரவுடனும் வழிகாட்டுதல் இணைந்து செயல்படலாம்." },
    ], note: "வழிகாட்டிகளின் பெயர்கள், கிடைக்கும் நேரம், இணைக்கும் விதிகள், அமர்வு அட்டவணைகள் இன்னும் வெளியிடப்படவில்லை.", next: { label: "வளங்களை ஆராயுங்கள்", path: "/pages/resources" } },
  },
  {
    slug: "success-stories", group: "support",
    en: { title: "Stories from the journey", eyebrow: "Success stories", intro: "As participant stories are approved for publication, this space will share experiences and lessons from their entrepreneurship journeys.", sections: [
      { heading: "Real experiences", body: "Published stories will reflect the person’s own path, the work involved, and what they learned along the way." },
      { heading: "Lessons you can use", body: "Stories can offer perspective on turning ideas into action without promising that every journey will look the same." },
    ], note: "No individual stories are presented until they are approved and published.", next: { label: "View published stories", path: "/content/testimonial" } },
    ta: { title: "பயணக் கதைகள்", eyebrow: "வெற்றிக் கதைகள்", intro: "பங்கேற்பாளர்களின் கதைகள் வெளியீட்டுக்கு ஒப்புதல் பெறும்போது, அவர்களின் தொழில்முனைவுப் பயண அனுபவங்களையும் கற்றல்களையும் இங்கே பகிரலாம்.", sections: [
      { heading: "உண்மையான அனுபவங்கள்", body: "வெளியிடப்படும் கதைகள் அந்த நபரின் பாதை, அவர் செய்த வேலை, அதில் கற்றவை ஆகியவற்றைப் பிரதிபலிக்கும்." },
      { heading: "உதவும் கற்றல்கள்", body: "ஒவ்வொருவரின் பயணமும் ஒன்றுபோல் இருக்கும் என்று உறுதி செய்யாமல், யோசனையைச் செயலாக்கும் அனுபவத்தை கதைகள் காட்டலாம்." },
    ], note: "ஒப்புதல் பெற்று வெளியிடப்படும் வரை எந்த நபரின் கதையும் இங்கே இடம்பெறாது.", next: { label: "வெளியிடப்பட்ட கதைகள்", path: "/content/testimonial" } },
  },
  {
    slug: "resources", group: "support",
    en: { title: "Resources", eyebrow: "Keep learning", intro: "Find public learning material and practical references here as the program publishes them.", sections: [
      { heading: "Start with the basics", body: "Resources may help you explore business ideas, customers, planning, and the work of running a venture." },
      { heading: "Use trusted material", body: "Program teams can publish approved articles, documents, and links for public use." },
      { heading: "Go deeper when enrolled", body: "Participants may find additional course materials inside their learning area when their program provides them." },
    ], note: "Downloads and resource links appear only after they are reviewed and published.", next: { label: "Explore schemes", path: "/pages/schemes" } },
    ta: { title: "வளங்கள்", eyebrow: "தொடர்ந்து கற்றல்", intro: "திட்டம் வெளியிடும் போது பொது கற்றல் பொருட்களையும் நடைமுறைத் தகவல்களையும் இங்கே காணலாம்.", sections: [
      { heading: "அடிப்படைகளில் தொடங்குங்கள்", body: "தொழில் யோசனைகள், வாடிக்கையாளர்கள், திட்டமிடல், தொழிலை நடத்தும் வேலை ஆகியவற்றை ஆராய வளங்கள் உதவலாம்." },
      { heading: "நம்பகமான தகவல்", body: "திட்டக் குழுக்கள் பொது பயன்பாட்டுக்கான ஒப்புதல் பெற்ற கட்டுரைகள், ஆவணங்கள், இணைப்புகளை வெளியிடலாம்." },
      { heading: "சேர்ந்த பிறகு மேலும் கற்கலாம்", body: "திட்டம் வழங்கினால் பங்கேற்பாளர்கள் தங்கள் கற்றல் பகுதியில் கூடுதல் பாடப் பொருட்களைப் பார்க்கலாம்." },
    ], note: "மதிப்பாய்வு செய்யப்பட்டு வெளியிடப்பட்ட பின்னரே பதிவிறக்கங்களும் வள இணைப்புகளும் தோன்றும்.", next: { label: "திட்டங்களை ஆராயுங்கள்", path: "/pages/schemes" } },
  },
  {
    slug: "schemes", group: "support",
    en: { title: "Schemes", eyebrow: "Public opportunities", intro: "Explore schemes that may be relevant to entrepreneurship once verified information is published here.", sections: [
      { heading: "Understand the fit", body: "Each published scheme should explain its purpose, who it is for, and where to confirm current conditions." },
      { heading: "Check official sources", body: "Rules, deadlines, and availability can change. Always confirm details with the responsible scheme provider." },
      { heading: "Prepare your next step", body: "Use the information to decide what to investigate, what documents to gather, and whom to contact." },
    ], note: "Listing a scheme does not mean you are eligible or that support is guaranteed.", next: { label: "Explore funding opportunities", path: "/pages/funding-opportunities" } },
    ta: { title: "திட்டங்கள்", eyebrow: "பொது வாய்ப்புகள்", intro: "சரிபார்க்கப்பட்ட தகவல்கள் வெளியிடப்படும் போது தொழில்முனைவுக்கு தொடர்புடைய திட்டங்களை இங்கே ஆராயலாம்.", sections: [
      { heading: "பொருத்தத்தைப் புரிந்துகொள்ளுங்கள்", body: "வெளியிடப்படும் ஒவ்வொரு திட்டமும் அதன் நோக்கம், யாருக்கானது, தற்போதைய விதிகளை எங்கே உறுதிப்படுத்துவது என்பதைக் கூற வேண்டும்." },
      { heading: "அதிகாரப்பூர்வ ஆதாரங்களைப் பாருங்கள்", body: "விதிகள், கடைசி தேதிகள், கிடைக்கும் நிலை மாறலாம். பொறுப்பான திட்ட வழங்குநரிடம் விவரங்களை உறுதிப்படுத்துங்கள்." },
      { heading: "அடுத்த படிக்குத் தயாராகுங்கள்", body: "எதை ஆராய வேண்டும், எந்த ஆவணங்களைச் சேகரிக்க வேண்டும், யாரைத் தொடர்புகொள்ள வேண்டும் என்பதைக் தீர்மானிக்க தகவலைப் பயன்படுத்துங்கள்." },
    ], note: "ஒரு திட்டம் பட்டியலிடப்படுவது உங்களுக்குத் தகுதி உண்டு அல்லது ஆதரவு உறுதி என்று பொருளல்ல.", next: { label: "நிதி வாய்ப்புகளை ஆராயுங்கள்", path: "/pages/funding-opportunities" } },
  },
  {
    slug: "funding-opportunities", group: "support",
    en: { title: "Funding opportunities", eyebrow: "Explore what may be possible", intro: "Funding information can help you understand available routes and prepare stronger questions for providers.", sections: [
      { heading: "Discover", body: "Published opportunities may include grants, loans, or other support relevant to different stages of a venture." },
      { heading: "Compare conditions", body: "Look at purpose, eligibility, deadlines, documents, and obligations before deciding to apply." },
      { heading: "Plan responsibly", body: "A business plan can help clarify the amount you need, how it may be used, and what the next steps are." },
    ], note: "No funding is offered or guaranteed by this page. Confirm all terms with the official provider.", next: { label: "Return to resources", path: "/pages/resources" } },
    ta: { title: "நிதி வாய்ப்புகள்", eyebrow: "சாத்தியங்களை ஆராயுங்கள்", intro: "கிடைக்கும் வழிகளைப் புரிந்துகொள்ளவும் வழங்குநர்களிடம் தெளிவான கேள்விகளை கேட்கவும் நிதித் தகவல்கள் உதவலாம்.", sections: [
      { heading: "கண்டறியுங்கள்", body: "வெளியிடப்படும் வாய்ப்புகளில் மானியம், கடன் அல்லது தொழிலின் வெவ்வேறு கட்டங்களுக்கு ஏற்ற பிற ஆதரவு இடம்பெறலாம்." },
      { heading: "நிபந்தனைகளை ஒப்பிடுங்கள்", body: "விண்ணப்பிப்பதற்கு முன் நோக்கம், தகுதி, காலக்கெடு, ஆவணங்கள், பொறுப்புகள் ஆகியவற்றைப் பாருங்கள்." },
      { heading: "பொறுப்புடன் திட்டமிடுங்கள்", body: "தேவையான தொகை, அதன் பயன்பாடு, அடுத்த படிகள் ஆகியவற்றைத் தெளிவுபடுத்த தொழில் திட்டம் உதவும்." },
    ], note: "இந்தப் பக்கம் நிதியை வழங்கவோ உறுதி செய்யவோ இல்லை. அனைத்து நிபந்தனைகளையும் அதிகாரப்பூர்வ வழங்குநரிடம் உறுதிப்படுத்துங்கள்.", next: { label: "வளங்களுக்குத் திரும்புங்கள்", path: "/pages/resources" } },
  },
  {
    slug: "contact", group: "connect",
    en: { title: "Contact and support", eyebrow: "Get in touch", intro: "Questions about the program belong here. Published contact channels and enquiry instructions will be shown when the program opens them.", sections: [
      { heading: "Program information", body: "For eligibility, training, and application questions, first check the latest published pages and frequently asked questions." },
      { heading: "Your application", body: "If you already have an account, sign in to view your application and any messages about your next step." },
      { heading: "Contact details", body: "The program team will publish verified phone, email, or enquiry channels here. No unverified contact details are listed." },
    ], note: "A public enquiry channel is not open on this page yet.", next: { label: "Read the FAQs", path: "/content/faq" } },
    ta: { title: "தொடர்பும் ஆதரவும்", eyebrow: "தொடர்பு கொள்ளுங்கள்", intro: "திட்டம் குறித்த கேள்விகளுக்கான இடம் இது. திட்டம் திறக்கும் போது வெளியிடப்பட்ட தொடர்பு வழிகளும் விசாரணை வழிமுறைகளும் இங்கே காட்டப்படும்.", sections: [
      { heading: "திட்டத் தகவல்கள்", body: "தகுதி, பயிற்சி, விண்ணப்பம் குறித்த கேள்விகளுக்கு முதலில் சமீபத்திய வெளியிடப்பட்ட பக்கங்களையும் அடிக்கடி கேட்கப்படும் கேள்விகளையும் பாருங்கள்." },
      { heading: "உங்கள் விண்ணப்பம்", body: "ஏற்கனவே கணக்கு இருந்தால் உள்நுழைந்து விண்ணப்பத்தையும் அடுத்த படி குறித்த செய்திகளையும் பாருங்கள்." },
      { heading: "தொடர்பு விவரங்கள்", body: "சரிபார்க்கப்பட்ட தொலைபேசி, மின்னஞ்சல் அல்லது விசாரணை வழிகளைத் திட்டக் குழு இங்கே வெளியிடும். உறுதிப்படுத்தப்படாத விவரங்கள் பட்டியலிடப்படவில்லை." },
    ], note: "இந்தப் பக்கத்தில் பொது விசாரணை வழி இன்னும் திறக்கப்படவில்லை.", next: { label: "கேள்வி பதில்களைப் படியுங்கள்", path: "/content/faq" } },
  },
  {
    slug: "apply", group: "connect",
    en: { title: "How to apply", eyebrow: "Take the next step", intro: "When applications open for a program, your account is the place to start, save, submit, and follow your application.", sections: [
      { heading: "1. Check the program", body: "Read the current eligibility rules, application dates, and document requirements before you begin." },
      { heading: "2. Complete your application", body: "Provide the requested personal information and describe your entrepreneurship interest or business idea. Save a draft if you need more time." },
      { heading: "3. Follow the process", body: "After submission, use your account to track review, selection, and any communication about next steps." },
    ], note: "Application windows and program-specific rules are published by the program team. An account alone does not mean an application is open.", next: { label: "Open your account", path: "/account" } },
    ta: { title: "விண்ணப்பிப்பது எப்படி", eyebrow: "அடுத்த படி", intro: "திட்டத்திற்கான விண்ணப்பங்கள் திறக்கும்போது, உங்கள் கணக்கில் விண்ணப்பத்தைத் தொடங்கவும் சேமிக்கவும் சமர்ப்பிக்கவும் அதன் நிலையைப் பார்க்கவும் முடியும்.", sections: [
      { heading: "1. திட்டத்தைச் சரிபாருங்கள்", body: "தொடங்குவதற்கு முன் தற்போதைய தகுதி விதிகள், விண்ணப்ப தேதிகள், ஆவணத் தேவைகளைப் படியுங்கள்." },
      { heading: "2. விண்ணப்பத்தை முடிக்குங்கள்", body: "கேட்கப்படும் தனிப்பட்ட தகவல்களை அளித்து தொழில்முனைவு ஆர்வம் அல்லது தொழில் யோசனையை விவரியுங்கள். மேலும் நேரம் தேவைப்பட்டால் வரைவாகச் சேமியுங்கள்." },
      { heading: "3. நிலையைப் பாருங்கள்", body: "சமர்ப்பித்த பிறகு மதிப்பாய்வு, தேர்வு, அடுத்த படிகள் குறித்த தகவல்களை உங்கள் கணக்கில் பாருங்கள்." },
    ], note: "விண்ணப்பக் காலங்களையும் திட்ட விதிகளையும் திட்டக் குழு வெளியிடும். கணக்கு இருப்பதால் மட்டும் விண்ணப்பம் திறந்துள்ளது என்று பொருளல்ல.", next: { label: "உங்கள் கணக்கைத் திறக்கவும்", path: "/account" } },
  },
] as const;

export const starterPage = (locale: Locale, slug: string): StarterPage | undefined =>
  starterPages.find((page) => page.slug === slug)?.[locale];

export const starterPageList = (locale: Locale) =>
  starterPages.map((page) => ({ slug: page.slug, title: page[locale].title, group: page.group }));

export const publicNavLabels = {
  en: { program: "The program", support: "Explore", updates: "Updates", home: "Home", contact: "Contact", apply: "Apply", account: "Account", all: "All pages", news: "News", events: "Events", faq: "FAQ", stories: "Stories" },
  ta: { program: "திட்டம்", support: "ஆராயுங்கள்", updates: "புதியவை", home: "முகப்பு", contact: "தொடர்பு", apply: "விண்ணப்பம்", account: "கணக்கு", all: "அனைத்து பக்கங்களும்", news: "செய்திகள்", events: "நிகழ்வுகள்", faq: "கேள்வி பதில்கள்", stories: "கதைகள்" },
} as const;
