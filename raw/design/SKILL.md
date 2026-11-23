---
name: design
description: Design, implement, and review Visor UI using cream surfaces, ink black text and secondary buttons, and burnt orange primary actions. Use for frontend screens, components, responsive layouts, and interaction polish; not backend-only work.
---

# Visor UI design

Create a calm, modern developer workspace with clear hierarchy and restrained emphasis. Cream, ink black, and burnt orange are the brand palette. Apply this skill to the UI requested by the user; loading it does not authorize a full application redesign.

## Palette and tokens

Use [assets/tokens.css](assets/tokens.css) as the canonical source of color, spacing, radius, typography, and motion values. Reuse or map these semantic tokens into the project's existing styling system instead of scattering hex values through components.

| Color role | Usage |
| --- | --- |
| Cream | Page backgrounds, navigation, panels, cards, forms, and overlays; use the supplied cream shades for depth. |
| Ink black | Headings, body text, icons, and selected secondary buttons; cream text on filled ink buttons. |
| Burnt orange | The main action in a decision area, important feature accents, and selected indicators; cream text on filled orange buttons. |
| Muted ink and borders | Secondary text, supporting metadata, dividers, and control boundaries. |

Prefer one visually dominant orange action per decision area. Examples include importing a repository, starting a review, and starting Scrum Live. Highlight a main feature with an orange icon, label, or small accent against cream; keep large surfaces cream so emphasis remains meaningful.

Keep additional colors limited to existing semantic statuses or meaningful data series. Do not reuse orange as a generic error color or replace every status with the same accent. Soft decorative borders are not sufficient as the sole boundary of a form control; use the stronger control-border token where needed.

## Fit the existing project

- Inspect the affected components and shared styles before editing. Visor currently uses React/Vite, plain CSS in `client/src/styles.css`, and shared components under `client/src/components/`.
- Copy or map the token declarations into the existing client theme. Keep runtime styles inside `client/`: the frontend Docker build includes that directory only, so importing directly from `raw/design/` would break the image build.
- Preserve the existing Fraunces display and Space Grotesk body pairing unless the user chooses another font. Use monospace for code, commit hashes, and identifiers.
- Reuse the existing component and icon patterns. Improve shared components when the same requested correction affects several consumers.
- When restyling a requested area, migrate its old khaki, sage, or unrelated brand accents to the new palette. Avoid a second competing theme or a global repaint during a narrow component task.
- Keep routes, API behavior, permissions, and working interactions intact while making visual changes.

## Visual hierarchy

- Put the page title, useful context, and main action together. Use spacing and alignment to group related content before adding extra containers or rules.
- Use the supplied spacing scale: 4, 8, 12, 16, 24, 32, 48, and 64px. Start with 16–24px panel padding and 24–32px between major groups; adapt to the screen's density.
- Keep short page headings distinct from body text. Use approximately 1.1–1.2 heading line height and 1.5 body line height. Body and mobile input text should generally be 16px; controls and regularly read labels at least 14px.
- Use 10px control corners, 16px cards, and 20px overlays as starting points. Shadows communicate elevation for menus and overlays; normal cards need little or none.
- Favor opaque cream surfaces, readable content, and clear edges. Avoid decorative gradients, pervasive glass effects, excessive pills, and making every section a card.

## Components and behavior

| Component | Treatment |
| --- | --- |
| Primary button | Burnt orange fill, cream label, darker orange hover; name the action clearly. |
| Secondary button | Ink fill with cream label when strong secondary emphasis is needed; otherwise cream/transparent with ink text and a visible boundary. |
| Navigation | Ink labels on cream; use a small orange marker or soft orange tint for the active destination, with a non-color cue such as weight or an indicator. |
| Inputs | Cream raised surface, ink value, persistent label, stronger control border, and a visible focus ring. |
| Cards and tables | Cream surfaces, shared alignment, restrained dividers; align actions and changing numbers consistently. |
| Toasts | Compact cream surface, ink message, clear status icon/text, and a distinct action. Preserve existing timer, pause, and undo behavior; offer Undo only when it really reverses the change. |
| Dialogs | Cream panel, ink heading, one clear primary action, and a reachable cancel/close control. Preserve focus trapping and restoration. |
| Empty and error states | Explain what happened and offer the next useful action. Keep field validation near the field; reserve toasts for transient operation feedback. |

Provide hover, focus, pressed, disabled, loading, success, and error states where relevant. Keep an in-flight action visibly busy and prevent duplicate submissions. Status announcements should not steal keyboard focus.

## Responsive layouts and accessibility

- Reflow the task for narrow screens rather than shrinking the desktop. Stack related fields and actions in reading order; keep the primary action reachable.
- Use content-driven breakpoints. Check approximately 390px and a desktop width, plus smaller widths when the component is likely to overflow.
- Keep page-wide horizontal overflow out of the layout. Confine dense tables or Kanban columns to a clearly bounded scroll region when stacking would destroy their meaning.
- Aim for 44px touch targets. Give icon-only controls accessible names and retain visible labels for form fields.
- Check rendered contrast: at least 4.5:1 for ordinary text and 3:1 for large text and required control/focus indicators. Measure actual state pairs, including tinted and hover surfaces.
- Use semantic controls, keyboard access, and a visible focus indicator. Convey status through text or icons as well as color.

## Motion

Use motion to explain a state change, not to decorate routine work. Start with 140–200ms transitions for controls and short overlay entrances; frequent actions should feel immediate. Prefer opacity and transform, keep transitions interruptible, and avoid `transition: all`.

Respect `prefers-reduced-motion`. Keep static content immediately readable; avoid blur entrances, bouncing utility controls, automatic list staggers, and persistent pulsing. Preserve timers and functional feedback when reducing visual motion.

## Existing references

Read only the sections relevant to the requested work:

| Reference | When to consult it |
| --- | --- |
| [better-interface.md](better-interface.md) | Reviewing accessibility, layout, interface wording, typography, or component polish. |
| [desktop-to-mobile.md](desktop-to-mobile.md) | Adapting a desktop screen to mobile, especially navigation, forms, tables, and content order. |
| [design-motion.md](design-motion.md) | Choosing or reviewing interaction timing, transitions, and reduced-motion behavior. |

These are supplemental references from several workflows. For React work, translate applicable frame guidance into layout code; frame creation applies only to design-file tasks. Do not assume the imported references' tools, external workflow files, or report templates exist. Their general heuristics do not override this palette, the user's task, or established product behavior.

## Verification and handoff

When implementing UI, run the existing frontend build and checks appropriate to the change. Inspect the affected flow at desktop and mobile sizes when browser tools are available, including keyboard and loading/error states. Report which behavior was checked and any verification limit; do not claim a visual review from a build alone.

For review-only requests, report concrete findings without editing application code. For implementation requests, finish the working interaction and summarize the visible change, relevant checks, and any material limitation.
