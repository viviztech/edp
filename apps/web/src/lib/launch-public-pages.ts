import type { StarterPage } from "./public-site-content";

type Entry = {
  slug: string;
  group: "program" | "support" | "connect";
  en: StarterPage;
  ta: StarterPage;
};

export const launchPages: readonly Entry[] = [
  {
    slug: "about",
    group: "program",
    en: {
      title: "About the program",
      eyebrow: "Ideas into action",
      intro:
        "The Entrepreneurship Development Program from the Center for Social Justice and Equity brings practical learning, guidance and business planning into one connected journey.",
      sections: [
        {
          heading: "Start where you are",
          body: "Explore entrepreneurship with an early idea, a question or a goal. Use the public resources to think about your customers, the problem you want to solve and your next step.",
        },
        {
          heading: "Learn with a purpose",
          body: "The program approach connects business fundamentals with activities, conversations and planning, so learning has a place in your own idea.",
        },
        {
          heading: "Build a clearer path",
          body: "Talk with the program team about participation and the support appropriate to your stage. Start today with the idea planner.",
        },
      ],
      next: { label: "Make your first plan", path: "/tools/idea-planner" },
    },
    ta: {
      title: "திட்டம் பற்றி",
      eyebrow: "யோசனையிலிருந்து செயல்",
      intro:
        "சமூக நீதி மற்றும் சமத்துவ மையத்தின் தொழில்முனைவோர் மேம்பாட்டுத் திட்டம் நடைமுறைக் கற்றல், வழிகாட்டுதல், தொழில் திட்டமிடல் ஆகியவற்றை இணைக்கிறது.",
      sections: [
        {
          heading: "உங்கள் நிலையிலிருந்து தொடங்குங்கள்",
          body: "ஒரு ஆரம்ப யோசனை, கேள்வி அல்லது இலக்குடன் தொழில்முனைவை ஆராயுங்கள். வாடிக்கையாளர்கள், தீர்க்க விரும்பும் பிரச்சினை, அடுத்த படி ஆகியவற்றைப் பற்றி சிந்திக்க பொது வளங்களைப் பயன்படுத்துங்கள்.",
        },
        {
          heading: "நோக்கத்துடன் கற்றல்",
          body: "தொழில் அடிப்படைகளைச் செயல்பாடுகள், உரையாடல்கள், திட்டமிடலுடன் இணைத்து உங்கள் யோசனைக்குப் பயன்படுத்த உதவும் அணுகுமுறை.",
        },
        {
          heading: "தெளிவான பாதையை உருவாக்குங்கள்",
          body: "பங்கேற்பு மற்றும் உங்கள் நிலைக்குப் பொருத்தமான ஆதரவு குறித்து திட்டக் குழுவுடன் பேசுங்கள். யோசனைத் திட்டமிடலுடன் இன்றே தொடங்குங்கள்.",
        },
      ],
      next: {
        label: "முதல் திட்டத்தை உருவாக்குங்கள்",
        path: "/tools/idea-planner",
      },
    },
  },
  {
    slug: "eligibility",
    group: "program",
    en: {
      title: "Is this the right next step?",
      eyebrow: "Explore participation",
      intro:
        "Start by thinking about what you want to learn and where you are in your entrepreneurship journey. The program team can help you understand participation for the relevant intake.",
      sections: [
        {
          heading: "Your starting point",
          body: "Are you exploring an idea, preparing to start or developing an existing venture? Describe your stage and the questions you want to work through.",
        },
        {
          heading: "Your learning goals",
          body: "Think about the business skills, guidance and practical experience you need. Write down the time you can commit and any support you may need to take part.",
        },
        {
          heading: "Confirm the intake requirements",
          body: "Ask the program team about the current intake, eligibility, dates, location, fees and documents before making a commitment. An enquiry does not reserve a place or confirm admission.",
        },
      ],
      next: { label: "Discuss participation", path: "/pages/contact" },
    },
    ta: {
      title: "இது உங்கள் அடுத்த படியா?",
      eyebrow: "பங்கேற்பை அறியுங்கள்",
      intro:
        "என்ன கற்றுக்கொள்ள விரும்புகிறீர்கள், உங்கள் தொழில்முனைவுப் பயணத்தில் எங்கே இருக்கிறீர்கள் என்பதைச் சிந்தியுங்கள். பொருத்தமான சேர்க்கை குறித்து திட்டக் குழுவிடம் அறியலாம்.",
      sections: [
        {
          heading: "உங்கள் தொடக்கம்",
          body: "யோசனையை ஆராய்கிறீர்களா, தொழில் தொடங்கத் தயாராகிறீர்களா அல்லது உள்ள தொழிலை வளர்க்கிறீர்களா? உங்கள் நிலையையும் கேள்விகளையும் விவரியுங்கள்.",
        },
        {
          heading: "கற்றல் இலக்குகள்",
          body: "தேவையான தொழில் திறன்கள், வழிகாட்டுதல், அனுபவம் குறித்து சிந்தியுங்கள். ஒதுக்கக்கூடிய நேரத்தையும் பங்கேற்கத் தேவையான ஆதரவையும் எழுதுங்கள்.",
        },
        {
          heading: "சேர்க்கை விதிகளை உறுதிப்படுத்துங்கள்",
          body: "தற்போதைய சேர்க்கை, தகுதி, தேதிகள், இடம், கட்டணம், ஆவணங்கள் குறித்து முடிவெடுக்கும் முன் திட்டக் குழுவிடம் கேளுங்கள். விசாரணை இடத்தை முன்பதிவு செய்யவோ சேர்க்கையை உறுதி செய்யவோ இல்லை.",
        },
      ],
      next: { label: "பங்கேற்பு பற்றி பேசுங்கள்", path: "/pages/contact" },
    },
  },
  {
    slug: "benefits",
    group: "program",
    en: {
      title: "Learning that moves your idea forward",
      eyebrow: "The program approach",
      intro:
        "Connect the essentials of business with the decisions you need to make: what to offer, who it is for and how to take the next step.",
      sections: [
        {
          heading: "Practical business thinking",
          body: "Explore customer needs, your offer, everyday operations and a simple business plan. Use the idea worksheet to organize your first thoughts.",
        },
        {
          heading: "Conversations that help",
          body: "Mentoring and program guidance help participants question assumptions, review progress and choose practical next actions.",
        },
        {
          heading: "A plan you can build on",
          body: "Turn learning into a working plan, then revisit it as you learn from customers and experience. Ask the team which activities are included in your intake.",
        },
      ],
      next: {
        label: "Explore the learning approach",
        path: "/pages/training-structure",
      },
    },
    ta: {
      title: "யோசனையை முன்னேற்றும் கற்றல்",
      eyebrow: "திட்ட அணுகுமுறை",
      intro:
        "எதை வழங்குவது, யாருக்காக வழங்குவது, அடுத்த படியை எப்படி எடுப்பது போன்ற முடிவுகளுடன் தொழில் அடிப்படைகளை இணைக்கவும்.",
      sections: [
        {
          heading: "நடைமுறை தொழில் சிந்தனை",
          body: "வாடிக்கையாளர் தேவைகள், உங்கள் சேவை, அன்றாட செயல்பாடுகள், எளிய தொழில் திட்டம் ஆகியவற்றை ஆராயுங்கள். முதல் எண்ணங்களை ஒழுங்குபடுத்த யோசனைப் பயிற்சித்தாளைப் பயன்படுத்துங்கள்.",
        },
        {
          heading: "உதவும் உரையாடல்கள்",
          body: "ஊகங்களை ஆராயவும் முன்னேற்றத்தைப் பார்க்கவும் நடைமுறை நடவடிக்கைகளைத் தேர்ந்தெடுக்கவும் வழிகாட்டுதலும் திட்ட ஆதரவும் உதவுகின்றன.",
        },
        {
          heading: "வளர்த்துக்கொள்ளும் திட்டம்",
          body: "கற்றலை நடைமுறைத் திட்டமாக மாற்றி வாடிக்கையாளர் அனுபவத்தின் அடிப்படையில் திருத்துங்கள். உங்கள் சேர்க்கையில் உள்ள செயல்பாடுகளைத் திட்டக் குழுவிடம் கேளுங்கள்.",
        },
      ],
      next: {
        label: "கற்றல் அணுகுமுறையை அறியுங்கள்",
        path: "/pages/training-structure",
      },
    },
  },
  {
    slug: "training-structure",
    group: "program",
    en: {
      title: "Learn. Practice. Reflect.",
      eyebrow: "How learning works",
      intro:
        "The learning approach moves from understanding an idea to applying business essentials and reviewing your progress.",
      sections: [
        {
          heading: "Understand the foundations",
          body: "Connect your idea to a customer need. Think about your offer, how it reaches people and the work required to deliver it.",
        },
        {
          heading: "Put ideas into practice",
          body: "Use activities and assignments to test your understanding. Build a plan, discuss questions and learn from feedback.",
        },
        {
          heading: "Review and take the next step",
          body: "Reflect on what you have learned and decide what to test next. Your intake determines the timetable, delivery format, assessment and any certificate requirements.",
        },
      ],
      next: { label: "Try the idea worksheet", path: "/tools/idea-planner" },
    },
    ta: {
      title: "கற்போம். பயிற்சி செய்வோம். சிந்திப்போம்.",
      eyebrow: "கற்றல் முறை",
      intro:
        "யோசனையைப் புரிந்துகொள்வதில் தொடங்கி தொழில் அடிப்படைகளைப் பயன்படுத்தி முன்னேற்றத்தை மதிப்பிடும் கற்றல் அணுகுமுறை.",
      sections: [
        {
          heading: "அடிப்படைகளைப் புரிந்துகொள்ளுங்கள்",
          body: "உங்கள் யோசனையை வாடிக்கையாளர் தேவையுடன் இணைக்கவும். என்ன வழங்குவது, மக்களை எப்படி அடைவது, வழங்குவதற்கான வேலை ஆகியவற்றைச் சிந்தியுங்கள்.",
        },
        {
          heading: "யோசனைகளைப் பயன்படுத்துங்கள்",
          body: "செயல்பாடுகள் மற்றும் பயிற்சிகள் மூலம் புரிதலைச் சோதிக்கவும். திட்டம் உருவாக்கி, கேள்விகளை விவாதித்து, பின்னூட்டத்திலிருந்து கற்றுக்கொள்ளுங்கள்.",
        },
        {
          heading: "மதிப்பிட்டு முன்னேறுங்கள்",
          body: "கற்றதைச் சிந்தித்து அடுத்து எதைச் சோதிப்பது என முடிவெடுங்கள். அட்டவணை, கற்றல் முறை, மதிப்பீடு, சான்றிதழ் விதிகள் சேர்க்கையைப் பொறுத்தவை.",
        },
      ],
      next: {
        label: "யோசனைப் பயிற்சித்தாளை முயலுங்கள்",
        path: "/tools/idea-planner",
      },
    },
  },
  {
    slug: "mentors",
    group: "program",
    en: {
      title: "A clearer next step, together",
      eyebrow: "Mentoring",
      intro:
        "Good guidance starts with a useful question. Mentoring supports participants as they work through decisions and turn goals into actions.",
      sections: [
        {
          heading: "Bring a focused question",
          body: "Describe the decision you are trying to make, what you have tried and what you have learned. A focused question makes a conversation more useful.",
        },
        {
          heading: "Agree on a next action",
          body: "Use the conversation to choose a small, practical action. Record what you will do and when you will review it.",
        },
        {
          heading: "Follow your progress",
          body: "Revisit your actions and goals as your idea develops. Discuss mentor arrangements and session availability with the program team for your intake.",
        },
      ],
      next: { label: "Prepare your idea", path: "/tools/idea-planner" },
    },
    ta: {
      title: "இணைந்து ஒரு தெளிவான அடுத்த படி",
      eyebrow: "வழிகாட்டுதல்",
      intro:
        "பயனுள்ள கேள்வியிலிருந்து நல்ல வழிகாட்டுதல் தொடங்குகிறது. முடிவுகளை ஆராய்ந்து இலக்குகளைச் செயலாக்கப் பங்கேற்பாளர்களுக்கு ஆதரவு அளிக்கிறது.",
      sections: [
        {
          heading: "குறிப்பிட்ட கேள்வியுடன் வாருங்கள்",
          body: "எடுக்க வேண்டிய முடிவு, முயன்றவை, கற்றவை ஆகியவற்றை விளக்குங்கள். தெளிவான கேள்வி உரையாடலைப் பயனுள்ளதாக்குகிறது.",
        },
        {
          heading: "அடுத்த செயலைத் தேர்ந்தெடுங்கள்",
          body: "ஒரு சிறிய நடைமுறை நடவடிக்கையைத் தேர்ந்தெடுக்க உரையாடலைப் பயன்படுத்துங்கள். செய்ய வேண்டியதையும் மீண்டும் பார்க்கும் நேரத்தையும் பதிவு செய்யுங்கள்.",
        },
        {
          heading: "முன்னேற்றத்தைப் பாருங்கள்",
          body: "யோசனை வளரும்போது செயல்களையும் இலக்குகளையும் மீண்டும் பாருங்கள். உங்கள் சேர்க்கைக்கான வழிகாட்டல் ஏற்பாடுகளைத் திட்டக் குழுவிடம் கேளுங்கள்.",
        },
      ],
      next: { label: "யோசனையைத் தயாரியுங்கள்", path: "/tools/idea-planner" },
    },
  },
  {
    slug: "resources",
    group: "support",
    en: {
      title: "Small tools. Useful next steps.",
      eyebrow: "Entrepreneurship resources",
      intro:
        "Start with practical questions that help you explain your idea, understand a customer and plan a small experiment.",
      sections: [
        {
          heading: "Describe the problem",
          body: "Write one sentence about the problem you want to solve and who experiences it. Keep the description specific enough that you could speak to a real customer about it.",
        },
        {
          heading: "Listen before you build",
          body: "Ask people how they handle the problem today, what is difficult and what they have already tried. Record their own words and separate what you heard from your assumptions.",
        },
        {
          heading: "Choose a small test",
          body: "Decide on one thing you want to learn, a simple way to test it and the evidence you will review. Use the worksheet below to keep your next step concrete.",
        },
      ],
      next: { label: "Open the idea planner", path: "/tools/idea-planner" },
    },
    ta: {
      title: "சிறிய கருவிகள். பயனுள்ள அடுத்த படிகள்.",
      eyebrow: "தொழில்முனைவு வளங்கள்",
      intro:
        "யோசனையை விளக்கவும் வாடிக்கையாளரைப் புரிந்துகொள்ளவும் சிறிய முயற்சியைத் திட்டமிடவும் உதவும் நடைமுறைக் கேள்விகளுடன் தொடங்குங்கள்.",
      sections: [
        {
          heading: "பிரச்சினையை விவரியுங்கள்",
          body: "தீர்க்க விரும்பும் பிரச்சினையையும் அதை எதிர்கொள்பவரையும் ஒரு வாக்கியத்தில் எழுதுங்கள். உண்மையான வாடிக்கையாளரிடம் பேசக்கூடிய அளவுக்குக் குறிப்பிட்டதாக இருக்கட்டும்.",
        },
        {
          heading: "உருவாக்கும் முன் கேளுங்கள்",
          body: "இப்போது பிரச்சினையை எப்படி சமாளிக்கிறார்கள், எது கடினம், ஏற்கனவே என்ன முயன்றார்கள் எனக் கேளுங்கள். அவர்களது சொற்களைப் பதிவு செய்து உங்கள் ஊகங்களிலிருந்து பிரித்துப் பாருங்கள்.",
        },
        {
          heading: "சிறிய சோதனையைத் தேர்ந்தெடுங்கள்",
          body: "கற்றுக்கொள்ள விரும்பும் ஒன்று, அதைச் சோதிக்கும் எளிய வழி, பார்க்க வேண்டிய ஆதாரம் ஆகியவற்றைத் தேர்ந்தெடுங்கள். அடுத்த படியைத் திட்டமிட கீழேயுள்ள பயிற்சித்தாளைப் பயன்படுத்துங்கள்.",
        },
      ],
      next: {
        label: "யோசனைத் திட்டமிடலைத் திறக்கவும்",
        path: "/tools/idea-planner",
      },
    },
  },
  {
    slug: "contact",
    group: "connect",
    en: {
      title: "Let’s talk about your next step",
      eyebrow: "Contact the program",
      intro:
        "Ask about participation, learning or guidance. Tell the team what you want to explore and the support that would help you move forward.",
      sections: [
        {
          heading: "A useful starting point",
          body: "Include your stage, your main question and the language you prefer. A short, clear message is enough to begin.",
        },
        {
          heading: "Keep your information private",
          body: "Do not send identity documents, bank details, passwords or sensitive records through a general enquiry. This channel is for program questions.",
        },
      ],
      next: { label: "Read the FAQs", path: "/content/faq" },
    },
    ta: {
      title: "உங்கள் அடுத்த படியைப் பற்றி பேசுவோம்",
      eyebrow: "திட்டத்தைத் தொடர்பு கொள்ளுங்கள்",
      intro:
        "பங்கேற்பு, கற்றல் அல்லது வழிகாட்டுதல் பற்றி கேளுங்கள். ஆராய விரும்புவதையும் தேவையான ஆதரவையும் குழுவிடம் பகிருங்கள்.",
      sections: [
        {
          heading: "பயனுள்ள தொடக்கம்",
          body: "உங்கள் நிலை, முக்கிய கேள்வி, விரும்பும் மொழி ஆகியவற்றைக் குறிப்பிடுங்கள். தொடங்க ஒரு சுருக்கமான தெளிவான செய்தி போதும்.",
        },
        {
          heading: "தனிப்பட்ட தகவலைப் பாதுகாக்கவும்",
          body: "பொது விசாரணையில் அடையாள ஆவணங்கள், வங்கித் தகவல்கள், கடவுச்சொற்கள் அல்லது முக்கிய ஆவணங்களை அனுப்ப வேண்டாம். இது திட்டக் கேள்விகளுக்கான வழி.",
        },
      ],
      next: { label: "கேள்வி பதில்களைப் படியுங்கள்", path: "/content/faq" },
    },
  },
  {
    slug: "apply",
    group: "connect",
    en: {
      title: "Find your route into the program",
      eyebrow: "Explore participation",
      intro:
        "Start a conversation with the program team about your interests and the relevant intake. Confirm the requirements before preparing an application.",
      sections: [
        {
          heading: "1. Explain your interest",
          body: "Share where you are in your journey, what you would like to learn and the questions you have about taking part.",
        },
        {
          heading: "2. Confirm the details",
          body: "Ask about eligibility, dates, fees, training format and documents. The program team will explain the application route for the relevant intake.",
        },
        {
          heading: "3. Prepare your next step",
          body: "Use the idea planner to organize your thoughts. An enquiry is an expression of interest, not an application, admission decision or funding commitment.",
        },
      ],
      next: { label: "Get in touch", path: "/pages/contact" },
    },
    ta: {
      title: "திட்டத்தில் சேரும் வழியை அறியுங்கள்",
      eyebrow: "பங்கேற்பை ஆராயுங்கள்",
      intro:
        "உங்கள் ஆர்வம் மற்றும் பொருத்தமான சேர்க்கை குறித்து திட்டக் குழுவுடன் உரையாடுங்கள். விண்ணப்பம் தயாரிக்கும் முன் விதிகளை உறுதிப்படுத்துங்கள்.",
      sections: [
        {
          heading: "1. ஆர்வத்தை விளக்குங்கள்",
          body: "உங்கள் பயண நிலை, கற்றுக்கொள்ள விரும்புவது, பங்கேற்பு குறித்த கேள்விகள் ஆகியவற்றைப் பகிருங்கள்.",
        },
        {
          heading: "2. விவரங்களை உறுதிப்படுத்துங்கள்",
          body: "தகுதி, தேதிகள், கட்டணம், பயிற்சி முறை, ஆவணங்கள் குறித்து கேளுங்கள். பொருத்தமான சேர்க்கைக்கான விண்ணப்ப வழியைத் திட்டக் குழு விளக்கும்.",
        },
        {
          heading: "3. அடுத்த படியைத் தயாரியுங்கள்",
          body: "எண்ணங்களை ஒழுங்குபடுத்த யோசனைத் திட்டமிடலைப் பயன்படுத்துங்கள். விசாரணை என்பது ஆர்வத்தை வெளிப்படுத்துவது; விண்ணப்பம், சேர்க்கை முடிவு அல்லது நிதி உறுதி அல்ல.",
        },
      ],
      next: { label: "தொடர்பு கொள்ளுங்கள்", path: "/pages/contact" },
    },
  },
  {
    slug: "privacy",
    group: "connect",
    en: {
      title: "Your information",
      eyebrow: "Privacy on this website",
      intro:
        "Use the public pages without creating an account. Share only the information needed for a program enquiry.",
      sections: [
        {
          heading: "Public browsing and tools",
          body: "The idea planner keeps your answers in memory in the current browser tab. It does not send those answers to the server or save them in browser storage. Download a copy if you want to keep it. Closing or refreshing the page clears your answers.",
        },
        {
          heading: "Enquiries",
          body: "When the enquiry form is available, it asks for your name, email, optional phone number and message, with your consent to respond. These details are stored in the program database and available to authorized staff. Do not include identity documents, financial records or passwords.",
        },
        {
          heading: "Sessions and service operation",
          body: "Essential cookies support sign-in and protect form submissions. The service records operational events for reliability and security. The public site does not include advertising trackers or third-party analytics.",
        },
        {
          heading: "Questions about your information",
          body: "Use the published contact channel to ask about information you have shared or to request its correction or removal. Include your enquiry reference when available; do not send a password.",
        },
      ],
      next: { label: "Contact the program", path: "/pages/contact" },
    },
    ta: {
      title: "உங்கள் தகவல்",
      eyebrow: "இணையதளத் தனியுரிமை",
      intro:
        "கணக்கு உருவாக்காமல் பொது பக்கங்களைப் பயன்படுத்தலாம். திட்ட விசாரணைக்குத் தேவையான தகவலை மட்டும் பகிருங்கள்.",
      sections: [
        {
          heading: "பொது பக்கங்களும் கருவிகளும்",
          body: "யோசனைத் திட்டமிடலின் பதில்கள் தற்போதைய உலாவித் தாவலின் நினைவகத்தில் இருக்கும். அவை சேவையகத்துக்கு அனுப்பப்படுவதில்லை; உலாவிச் சேமிப்பிலும் வைக்கப்படுவதில்லை. வைத்திருக்க நகலைப் பதிவிறக்குங்கள். பக்கத்தை மூடினாலோ புதுப்பித்தாலோ பதில்கள் அழியும்.",
        },
        {
          heading: "விசாரணைகள்",
          body: "விசாரணைப் படிவம் கிடைக்கும்போது பெயர், மின்னஞ்சல், விருப்பமான தொலைபேசி எண், செய்தி மற்றும் பதில் அளிப்பதற்கான சம்மதத்தைக் கேட்கும். தகவல் திட்டத் தரவுத்தளத்தில் சேமிக்கப்பட்டு அங்கீகரிக்கப்பட்ட பணியாளர்களுக்குக் கிடைக்கும். அடையாள ஆவணங்கள், நிதிப் பதிவுகள், கடவுச்சொற்களைச் சேர்க்க வேண்டாம்.",
        },
        {
          heading: "அமர்வுகளும் சேவை இயக்கமும்",
          body: "அத்தியாவசிய குக்கீகள் உள்நுழைவு மற்றும் படிவப் பாதுகாப்பிற்கு உதவுகின்றன. நம்பகத்தன்மை மற்றும் பாதுகாப்புக்காக இயக்க நிகழ்வுகள் பதிவு செய்யப்படுகின்றன. விளம்பரக் கண்காணிப்போ மூன்றாம் தரப்பு பகுப்பாய்வோ பொது தளத்தில் இல்லை.",
        },
        {
          heading: "தகவல் குறித்த கேள்விகள்",
          body: "பகிர்ந்த தகவல் குறித்து கேட்கவும் திருத்தம் அல்லது நீக்கம் கோரவும் வெளியிடப்பட்ட தொடர்பு வழியைப் பயன்படுத்துங்கள். இருந்தால் விசாரணை எண்ணைக் குறிப்பிடுங்கள்; கடவுச்சொல்லை அனுப்ப வேண்டாம்.",
        },
      ],
      next: {
        label: "திட்டத்தைத் தொடர்பு கொள்ளுங்கள்",
        path: "/pages/contact",
      },
    },
  },
];
