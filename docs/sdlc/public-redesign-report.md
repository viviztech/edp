# Public website redesign

The complete landing page and shared public experience have a new visual system: a floating navigation bar, bold Sora headings, a people-focused photographic hero, distinct learning/support cards, an interactive four-stage journey, helpful program links, FAQ, and a full footer. English and Tamil have matching content and responsive typography.

Supporting information pages use the same fonts, surfaces, navigation and footer. The FAQ page uses the landing page's program answers when no CMS questions are published; published CMS content still takes precedence. Program availability remains explicit.

## Design and implementation

- Cobalt `#2457E8`, ink `#142D4E`, cloud `#F7F9FC`, mist `#E9EEFD`, mint `#DFF5EA`, and sunshine `#FFDE82`.
- Locally hosted Sora, Hanken Grotesk, and Noto Sans Tamil variable fonts; OFL licenses are included with the font assets.
- Server-rendered page content with small client components for navigation and the journey selector.
- Mobile disclosure navigation, hover/touch dropdowns, Escape dismissal, focused keyboard tab navigation, native FAQ disclosure controls, visible focus indicators and reduced-motion support.
- Responsive Next.js image optimization, eager/high-priority hero loading, and no added application dependencies.

## Validation

- Production build and TypeScript validation passed.
- ESLint passed; frontend suite: 49 tests passed. The navigation/journey subset also passed all 7 interaction tests.
- Chrome checks passed at 1440, 1024, 390 and 320 pixels in English, and 1440 and 390 pixels in Tamil: 200 responses, one H1, loaded images, and no horizontal overflow.
- Mobile dropdown/Escape, Tamil journey destination selection, and FAQ pointer/keyboard behavior verified in the browser.
- About, Eligibility, Resources, the page directory and FAQ pages returned 200 and fit their tested layouts.
- Reduced-motion emulation disabled the hero animations.
- Production preview had no JavaScript errors. Final screenshots are in `output/playwright/redesign-{locale}-{width}.png`.

The local account session check depends on a backend service that was not running in the local preview environment. Account functionality and delivery-provider setup are outside this visual redesign; the deployed backend is checked during rollout.

## Artwork

Built-in imagegen was used for the hero; the original generated file was retained. The project-bound asset is `apps/web/public/images/entrepreneurs-hero.png` (1536 × 1024). The scene is illustrative and depicts fictional people, as reflected in the image alternative text.

Final generation prompt:

> Use case: photorealistic-natural. Asset type: an editorial photographic asset for the redesigned CSJE entrepreneurship program website, not a screenshot or website mockup. Create one high-quality candid, naturally lit photograph of a small group of three young adult South Indian entrepreneurs, two women and one man, collaborating around a light wood table in a welcoming contemporary community learning studio in Tamil Nadu. One woman in a simple indigo kurta is the central focus, warmly engaged as she shares a notebook business idea with the others; another person wears a muted sage shirt, another a soft cream top. Show notebooks, a few modest handmade products, and a laptop, with realistic hands. Confident, thoughtful, optimistic energy, authentic ordinary people rather than glamorous models. Background has softly blurred windows, a plant, a whiteboard without readable writing, and daylight. Editorial lifestyle photography, tactile natural skin and cotton fabric, rich but restrained cobalt/sage/neutral palette, clean photographic depth. Composition: landscape 3:2, medium-wide group portrait cropped around waist/table, subjects centered so it also crops well to a tall 4:5 hero panel. No text, logos, watermarks, infographic graphics, borders or UI. These are fictional illustrative people, do not depict a real identifiable person. Save at high visual quality.

## Publication

Published to the existing Coolify staging application `csje-edp`, on `deploy/coolify`, at https://edp.200.234.34.140.sslip.io/.

- Deployed commit: `bf6ac5ee1350f176db9d73b7c145b5f36be58b99`.
- Deployment: `n75m3uepm1ywfahmlg3qkewh`, finished on 13 October 2026; application status `running:healthy`.
- Live Chrome verification passed for English at 1440 and 390 pixels, Tamil at 390 pixels, and the FAQ page at 390 pixels: HTTP 200, loaded images, no horizontal overflow and no JavaScript errors.
- Live screenshots: `output/playwright/live-redesign-en-1440.png`, `live-redesign-en-390.png`, `live-redesign-ta-390.png`, and `live-redesign-en-content-faq-390.png`.
- HTTPS route checks passed for the root redirect, both locales, the account page and public assets. The deployed CSRF endpoint returned 200 with a valid response and a Secure cookie; the unauthenticated session endpoint returned the expected 401.
- The live account page completed its initial session check and displayed the sign-in form. Its only console error was the expected 401 resource response for an unauthenticated session.

Database migrations completed successfully and the API, database and Redis passed their deployment health checks. Deployment configuration and existing application secrets were preserved.
