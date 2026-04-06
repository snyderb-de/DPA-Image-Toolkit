# Design System: Digital Preservation Lab

## 1. Overview & Creative North Star
The Creative North Star for this system is **"The Digital Archivist."** 

This design system moves away from the sterile, high-velocity world of "SaaS Productivity" and enters the calm, high-precision environment of a preservation laboratory. It is built on the philosophy of *Intentional Preservation*: every pixel should feel as though it was handled with white gloves.

To break the "template" look, we utilize **Asymmetric Weighting** and **Tonal Depth**. Instead of standard centered grids, layouts should favor wide margins and editorial-inspired groupings. We treat the digital screen as a physical workspace—a light table or a darkroom—where elements are layered like vellum, contact sheets, and archival glass.

---

## 2. Colors & Surface Philosophy
The palette is rooted in the materials of the trade: charcoal, slate, parchment, and brass.

### The "No-Line" Rule
**Borders are prohibited for sectioning.** To define a sidebar, a header, or a main content area, you must use background color shifts. For example, a `surface-container-low` sidebar sitting against a `background` workspace. This creates a "molded" look rather than a "sketched" look.

### Surface Hierarchy & Nesting
Treat the UI as a series of stacked materials. Use the `surface-container` tiers to create a "recessed" or "elevated" feel:
- **Workspace (Base):** `surface` (#121416)
- **Primary Panels:** `surface-container-low` (#1a1c1e)
- **Nested Controls/Cards:** `surface-container` (#1e2022)
- **Floating Overlays:** `surface-bright` (#37393b) with 80% opacity and `backdrop-filter: blur(12px)`.

### The "Glass & Gradient" Rule
Standard flat colors feel static. To provide "visual soul," use subtle gradients.
- **CTAs:** Transition from `primary` (#e9c78b) to `primary-container` (#ccac72) at a 45-degree angle. This mimics the sheen of aged brass or silk ribbons used in archival binding.
- **Glass Panels:** Apply `surface-variant` at 60% opacity with a heavy blur to simulate frosted glass shelving.

---

## 3. Typography
The typography is an editorial dialogue between the modern precision of **Manrope** and the historical authority of **Newsreader**.

- **Display & Headlines (Newsreader):** Used for titles, screen headers, and archival labels. It suggests a curated, high-end museum catalog. 
- **UI & Body (Manrope):** Used for data, metadata, and functional controls. It represents the modern lab equipment used to analyze the past.

**Hierarchy as Identity:**
- **The "Folio" Header:** Use `display-sm` for page titles, but pair it with a `label-sm` (all caps, wide letter-spacing) sitting immediately above it to act as a "Catalog ID."
- **Metadata:** All image data should be set in `body-sm` or `label-md` using `on-surface-variant` (#d0c5b5) to ensure it feels secondary to the artifact being preserved.

---

## 4. Elevation & Depth
Depth is achieved through **Tonal Layering**, not structural shadows.

### The Layering Principle
Do not use shadows to separate a card from a background. Use the Spacing Scale to create a "moat" of empty space, and change the background token. 
*Example:* A `surface-container-highest` card on a `surface-container-low` background provides enough contrast to be distinct without a single line or shadow.

### Ambient Shadows
When an element must float (e.g., a context menu or a floating lab tool), use an **Ambient Shadow**:
- **Color:** A 10% opacity version of `on-surface` (#e2e2e5).
- **Blur:** Large (20px - 40px) with 0 spread.
- **Purpose:** To simulate an object sitting on a light table, creating a soft, natural glow rather than a harsh drop-shadow.

### The "Ghost Border" Fallback
If accessibility requirements demand a stroke, use the **Ghost Border**: `outline-variant` (#4d463a) at 15% opacity. It should be felt, not seen.

---

## 5. Components

### Buttons
- **Primary:** Gradient fill (`primary` to `primary-container`), `on-primary` text. No border. Roundedness: `md` (0.375rem).
- **Secondary:** Surface-only fill using `surface-container-highest`. 
- **Tertiary/Ghost:** Text-only in `primary-fixed-dim`. For use in low-priority archival actions.

### Chips (The "Catalog Tag")
Inspired by museum specimen labels. Use `surface-container-highest` with a `sm` (0.125rem) radius to keep them feeling slightly more rigid and professional. Use `on-surface-variant` for the text.

### Input Fields
- **Background:** `surface-container-lowest`.
- **Active State:** No heavy border; instead, the background shifts to `surface-container-high` and the `outline` (#998f81) becomes visible at 30% opacity.
- **Labels:** Always `label-md`, positioned above the field, never floating inside.

### Cards & Lists (The "Contact Sheet")
**Forbid the use of divider lines.** 
- Separate list items using a `0.5` (0.175rem) vertical gap and a slight shift to `surface-container-low` on hover.
- Cards should be grouped in clusters, mimicking the layout of a contact sheet or a drawer of archival boxes. Use `Spacing 4` (1.4rem) between groups.

### Tooltips
Minimalist and high-contrast. Use `surface-bright` with `on-surface` text. No arrows—just a simple, sharp-cornered rectangle (`sm` radius) that appears with a 200ms fade.

---

## 6. Do's and Don'ts

### Do:
- **Do** use intentional asymmetry. A wider left margin than a right margin can create a premium "editorial" feel.
- **Do** use `on-primary-container` for icons inside primary containers to maintain a monochromatic, sophisticated depth.
- **Do** lean into `surface-tint` for subtle overlays on images to make them feel "housed" within the app.

### Don't:
- **Don't** use 100% black. The deepest shade should be `surface-container-lowest` (#0c0e10) to maintain the "foggy grey" lab vibe.
- **Don't** use standard blue for links. Use `tertiary` (#bbd0d0) or `primary` (#e9c78b) to maintain the archival amber/slate palette.
- **Don't** use rapid, bouncy animations. All transitions should be "Linear" or "Ease-In-Out" over 300ms–500ms to feel "careful and enduring."