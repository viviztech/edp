# Design system pilot

Status: implemented for the public home and CMS page editor; the broader interface remains on existing styles.

## Direction

The Entrepreneurship Development Program uses an editorial paper-and-ink layout: ink headings, light paper, teal actions and a restrained copper highlight. The shared values live in `packages/design-tokens/tokens.json`. These tokens are provisional until brand approval. English and Tamil use the same palette; text remains live content and can wrap without truncation.

## Web

The Next.js app uses Tailwind CSS 4 and source-owned shadcn/ui components. `apps/web/components.json` records the CLI configuration. The pilot uses shadcn Card on the public home and shadcn Button, Input and Textarea in the staff CMS editor. Their source is under `apps/web/src/components/ui`, so visual changes are reviewed like other application code. Existing global styles remain in place for other screens. New component colors map to shared tokens in `apps/web/src/app/styles.css`, and the copper bar marks the public application notice.

Add further components through the pinned shadcn CLI, inspect its CSS changes, and keep existing brand tokens and localization intact. Use native labels, visible focus, disabled states and reduced-motion handling. Do not use visually styled controls that lack the underlying action or permission.

## Mobile

The Flutter app uses Material 3 with `EdpTheme.light()` in `apps/mobile/lib/theme/edp_theme.dart`. Its ink, background, teal, line and highlight values mirror the JSON tokens. This theme is the mobile foundation; future widgets should use `Theme.of(context).colorScheme` instead of embedded color values. Tamil uses the bundled Noto Sans Tamil font as a fallback so glyphs render consistently on Flutter web and devices; the existing localization flow remains in place.

## Pilot acceptance

The public page preserves localized heading, availability and navigation links at desktop and mobile widths. The staff editor preserves its required fields, permissions, versioned save behavior and status messaging. Web lint, typecheck, tests and production build; Flutter analyze, widget tests and web build are the local validation gates. Authenticated browser review and device review remain separate acceptance steps before a production design rollout.

## Completed-module frontend assets

The public home uses the original `apps/web/public/illustrations/program-path.svg` vector. It depicts a progression without implying program outcomes or participant data. It is decorative and hidden from assistive technology. Public page and editorial indexes, the account form, and the staff home use the same paper, ink, teal and copper vocabulary.

`StaffModuleNav` is the reusable module entry asset. Its tile variant forms the staff home; its compact variant connects the CMS, CRM, notifications and Meta screens. The component renders only links allowed by the selected organization grant. Server-side authorization on each destination remains the access boundary. The visual state uses `aria-current="page"`, and icon graphics are decorative because each link has a text label. The repaired Tamil CRM labels and new navigation descriptions are covered by frontend tests.

The staff design remains a frontend pass over completed modules, not a new feature or provider workflow. Pages without a matching grant keep the existing denied/redirect behavior. Authenticated browser and native mobile review are still needed before treating the whole interface as visually accepted.

The mobile home now has a Material 3 program notice and navigation cards for public pages and account access. It uses the same copper highlight and teal actions as the web entry point. `apps/mobile/assets/fonts/NotoSansTamil-Regular.ttf` comes from the [Noto Tamil project](https://notofonts.github.io/tamil/) under the SIL Open Font License; its `OFL.txt` is bundled alongside the font.
