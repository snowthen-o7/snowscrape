# SnowScrape Brand Guidelines

**Version:** 1.0
**Last Updated:** January 19, 2026
**Status:** Initial Release

---

## Brand Overview

SnowScrape is a modern, serverless web scraping platform that makes data extraction simple, scalable, and reliable. Our brand reflects professionalism, technical competence, and accessibility.

### Brand Personality

- **Professional** - Enterprise-grade reliability and security
- **Modern** - Cutting-edge serverless technology
- **Accessible** - Simple enough for beginners, powerful for experts
- **Trustworthy** - Transparent pricing, ethical practices
- **Innovative** - Continuous improvement and feature development

---

## Logo

### Primary Logo

**Symbol:** Snowflake + Data nodes
**Concept:** Represents the "Snow" in SnowScrape combined with interconnected data extraction

**Files:**
- `/public/logo/logo.svg` - Primary logo (color)
- `/public/logo/logo-dark.svg` - Dark mode variant
- `/public/logo/favicon.ico` - Favicon

### Logo Usage

**Minimum Size:**
- Digital: 32px height
- Print: 0.5 inches height

**Clear Space:**
- Maintain minimum padding of 50% logo height on all sides

**Do's:**
- Use on white, light gray, or brand primary backgrounds
- Maintain aspect ratio
- Use dark variant on dark backgrounds

**Don'ts:**
- Don't stretch or distort
- Don't add effects (drop shadows, glows)
- Don't place on busy backgrounds
- Don't rotate or alter colors

---

## Color Palette

### Primary Colors

#### Brand Primary - Deep Blue
```
Hex: #0A2540
RGB: 10, 37, 64
HSL: 210, 74%, 15%
Usage: Headers, CTAs, primary buttons, navigation
```

**Psychology:** Trust, professionalism, stability
**Accessibility:** Use white text on this color (WCAG AAA)

#### Brand Accent - Bright Cyan
```
Hex: #00D9FF
RGB: 0, 217, 255
HSL: 189, 100%, 50%
Usage: Highlights, links, interactive elements, gradients
```

**Psychology:** Energy, technology, innovation
**Accessibility:** Use dark text on this color

#### Brand Gradient
```
CSS: linear-gradient(135deg, #0A2540 0%, #00D9FF 100%)
Usage: Hero sections, feature cards, marketing materials
```

### Status Colors

#### Running - Blue
```
Hex: #3B82F6
Usage: Active jobs, in-progress states
```

#### Success - Green
```
Hex: #22C55E
Usage: Completed jobs, success messages
```

#### Failed - Red
```
Hex: #EF4444
Usage: Error states, failed jobs, destructive actions
```

#### Paused - Amber
```
Hex: #F59E0B
Usage: Paused jobs, warning states
```

#### Scheduled - Gray
```
Hex: #6B7280
Usage: Scheduled jobs, neutral states
```

### Semantic Colors

- **Success:** #22C55E - Confirmations, successful operations
- **Warning:** #F59E0B - Alerts, caution messages
- **Error:** #EF4444 - Errors, critical issues
- **Info:** #3B82F6 - Informational messages, tips

### Neutral Colors

- **Gray 50:** #F9FAFB - Backgrounds
- **Gray 100:** #F3F4F6 - Subtle backgrounds
- **Gray 200:** #E5E7EB - Borders
- **Gray 300:** #D1D5DB - Inactive elements
- **Gray 400:** #9CA3AF - Placeholder text
- **Gray 500:** #6B7280 - Secondary text
- **Gray 600:** #4B5563 - Primary text (light mode)
- **Gray 700:** #374151 - Headings
- **Gray 800:** #1F2937 - Dark backgrounds
- **Gray 900:** #111827 - Darkest backgrounds

---

## Typography

### Font Families

**Heading Font:** Geist Sans (already imported)
- Modern, geometric, highly readable
- Use for all headings, navigation, buttons

**Body Font:** Geist Sans
- Clean, professional, optimized for screens
- Use for all body text, UI elements

**Monospace Font:** Geist Mono
- Developer-friendly, highly legible
- Use for code snippets, JSON, API responses, configuration

### Type Scale

| Size | Pixels | Use Case |
|------|--------|----------|
| xs   | 12px   | Fine print, timestamps, metadata |
| sm   | 14px   | Secondary text, labels, captions |
| base | 16px   | Body text, form inputs |
| lg   | 18px   | Emphasized text, large labels |
| xl   | 20px   | Subheadings, card titles |
| 2xl  | 24px   | Section headings |
| 3xl  | 30px   | Page headings |
| 4xl  | 36px   | Feature headings |
| 5xl  | 48px   | Hero headings |
| 6xl  | 60px   | Marketing hero (desktop) |

### Font Weights

- **Normal (400):** Body text
- **Medium (500):** Emphasized text, labels
- **Semibold (600):** Subheadings, buttons
- **Bold (700):** Headings, strong emphasis

### Line Heights

- **Tight (1.25):** Large headings
- **Normal (1.5):** Body text, default
- **Relaxed (1.75):** Long-form content, documentation

### Typography Examples

**H1 - Page Heading:**
```
Font: Geist Sans
Size: 48px (3xl on mobile, 5xl on desktop)
Weight: Bold (700)
Line Height: Tight (1.25)
Color: Gray 900 (light mode), White (dark mode)
```

**H2 - Section Heading:**
```
Font: Geist Sans
Size: 30px (2xl on mobile, 3xl on desktop)
Weight: Semibold (600)
Line Height: Tight (1.25)
```

**Body Text:**
```
Font: Geist Sans
Size: 16px (base)
Weight: Normal (400)
Line Height: Normal (1.5)
Color: Gray 600
```

**Button Text:**
```
Font: Geist Sans
Size: 14px (sm) or 16px (base)
Weight: Medium (500)
Line Height: Normal (1.5)
```

---

## Spacing & Layout

### Spacing Scale

Based on 4px grid system:
- **xs:** 4px
- **sm:** 8px
- **md:** 16px (base unit)
- **lg:** 24px
- **xl:** 32px
- **2xl:** 48px
- **3xl:** 64px
- **4xl:** 96px
- **5xl:** 128px

### Layout Principles

1. **Consistent Spacing:** Use spacing scale for all margins and padding
2. **Vertical Rhythm:** Maintain consistent spacing between sections (2xl, 3xl)
3. **Whitespace:** Don't be afraid of empty space - it improves readability
4. **Alignment:** Align elements to a grid for visual harmony
5. **Hierarchy:** Use spacing to create clear visual hierarchy

---

## Visual Elements

### Borders

**Border Widths:**
- Thin: 1px - Default borders, dividers
- Medium: 2px - Focused inputs, active states
- Thick: 4px - Emphasis, feature cards

**Border Radius:**
- **sm (4px):** Small elements, badges
- **md (8px):** Buttons, inputs, cards (default)
- **lg (12px):** Large cards, modals
- **xl (16px):** Hero cards, feature sections
- **2xl (24px):** Marketing elements
- **full (9999px):** Pills, avatars, circular elements

### Shadows

**Elevation System:**
- **sm:** Subtle cards, inputs
- **md:** Cards, dropdowns (default)
- **lg:** Modals, popovers
- **xl:** Dialogs, overlays
- **2xl:** Hero sections, marketing cards

**Usage:**
- Use shadows to create depth and hierarchy
- Increase shadow on hover for interactive elements
- Dark mode: Use more subtle shadows

### Icons

**Icon Library:** Lucide React (already integrated)

**Sizes:**
- Small: 16px - Inline with text
- Base: 20px - Default UI icons
- Large: 24px - Feature cards, emphasis
- XL: 32px - Marketing sections
- 2XL: 48px - Hero sections

**Style:**
- Use outline style (not filled) for consistency
- Maintain 2px stroke width
- Align icons to optical center, not geometric center

---

## Component Patterns

### Buttons

**Primary Button:**
```
Background: Brand Primary (#0A2540)
Text: White
Hover: Lighten 10%
Border Radius: md (8px)
Padding: sm lg (8px 24px)
Shadow: sm, on hover: md
```

**Secondary Button:**
```
Background: Transparent
Border: 1px Brand Primary
Text: Brand Primary
Hover: Brand Primary background, White text
Border Radius: md (8px)
```

**Destructive Button:**
```
Background: Error (#EF4444)
Text: White
Hover: Darken 10%
```

### Cards

**Default Card:**
```
Background: White (dark: Gray 800)
Border: 1px Gray 200 (dark: Gray 700)
Border Radius: lg (12px)
Padding: lg (24px)
Shadow: md
Hover: shadow lg (for interactive cards)
```

### Badges

**Status Badges:**
- Background: Status color at 10% opacity
- Text: Status color
- Border: 1px status color at 20% opacity
- Border Radius: full (pill shape)
- Padding: xs sm (4px 8px)
- Font Size: xs (12px)
- Font Weight: Medium (500)

---

## Tone of Voice

### Writing Principles

1. **Professional but Approachable**
   - ❌ "Leverage our synergistic scraping paradigm"
   - ✅ "Extract data from any website with ease"

2. **Technical Accuracy Without Jargon**
   - ❌ "Implements headless browser orchestration via containerized chromium instances"
   - ✅ "Handles JavaScript-heavy sites with built-in browser rendering"

3. **Confidence Without Arrogance**
   - ❌ "We're the world's best scraping platform"
   - ✅ "Trusted by 1,000+ data teams for reliable scraping"

4. **Educational and Helpful**
   - Always explain "why" not just "what"
   - Provide examples and use cases
   - Link to documentation for more details

### Content Guidelines

**Do:**
- Use active voice ("Extract data" not "Data is extracted")
- Start sentences with verbs (action-oriented)
- Use contractions (it's, you're, we're) for approachability
- Keep sentences short and scannable
- Use bullet points and numbered lists
- Highlight benefits, not just features

**Don't:**
- Use excessive marketing superlatives
- Use technical jargon without explanation
- Write long paragraphs (3 sentences max)
- Use passive voice
- Use all caps (except acronyms)
- Overuse emojis (use sparingly for emphasis)

### Example Copy

**Good:**
> "Build scrapers in minutes, not hours. Our visual builder lets you point and click to extract data—no coding required."

**Bad:**
> "Our revolutionary, AI-powered, next-generation scraping solution leverages cutting-edge technology to facilitate data extraction."

---

## Imagery & Photography

### Photography Style

**Characteristics:**
- Clean, modern, well-lit
- Real people using computers (not stock photo clichés)
- Focus on screens showing actual product
- Natural poses, genuine expressions
- Diverse representation

**Avoid:**
- Overly posed corporate stock photos
- Fake "hacker" aesthetics (hoodie in dark room)
- Generic office photos
- Low-quality or pixelated images

### Illustrations

**Style:**
- Flat, isometric 2.5D style
- Limited color palette (brand colors + neutrals)
- Clean lines, geometric shapes
- Data/technology themes (servers, data flows, networks)
- Consistent illustration style across site

**Use Cases:**
- Empty states ("No jobs yet")
- Error pages (404, 500)
- Feature explanations (how it works)
- Marketing hero sections
- Onboarding tutorials

---

## Accessibility

### Color Contrast

**WCAG AA Compliance (Minimum):**
- Normal text: 4.5:1 contrast ratio
- Large text: 3:1 contrast ratio
- UI components: 3:1 contrast ratio

**WCAG AAA Compliance (Goal):**
- Normal text: 7:1 contrast ratio
- Large text: 4.5:1 contrast ratio

**Tested Combinations:**
- ✅ White text on Brand Primary (#0A2540) - AAA compliant
- ✅ Dark text on Brand Accent (#00D9FF) - AA compliant
- ✅ White text on Success (#22C55E) - AA compliant

### Accessibility Best Practices

1. **Color is not the only indicator**
   - Use icons + text, not just color
   - Example: Success badge shows ✓ icon + green color + "Success" text

2. **Keyboard Navigation**
   - All interactive elements must be keyboard accessible
   - Visible focus states required
   - Logical tab order

3. **Screen Readers**
   - Use semantic HTML (nav, main, article, etc.)
   - Provide alt text for all images
   - Use ARIA labels where needed
   - Ensure form inputs have labels

4. **Motion & Animation**
   - Respect prefers-reduced-motion
   - Keep animations subtle and purposeful
   - No auto-playing videos without controls

---

## Brand Applications

### Marketing Website

- Use brand gradient in hero section
- Predominantly white/light backgrounds
- Liberal use of whitespace
- Large, bold headings
- Clear CTAs with primary button style
- Feature sections with icons and illustrations
- Social proof (logos, testimonials) prominently displayed

### Application Dashboard

- Clean, functional UI
- Generous padding and spacing
- Status badges with appropriate colors
- Data visualizations using brand colors
- Subtle shadows for depth
- Quick actions easily accessible
- Real-time updates with visual feedback

### Email Communications

- Text-heavy, minimal images (for deliverability)
- Brand colors in headers/CTAs
- Clear subject lines
- Personalization where possible
- Mobile-responsive design
- Single, clear CTA per email

### Documentation

- Code syntax highlighting
- Inline code in monospace font
- Screenshots with captions
- Step-by-step numbered instructions
- Expandable sections for advanced topics
- Search functionality
- Version indicators

---

## File Naming Conventions

### Components

- PascalCase: `StatusBadge.tsx`, `JobCard.tsx`
- Descriptive names: Not `Card1.tsx` but `JobCard.tsx`

### Assets

- kebab-case: `logo-dark.svg`, `hero-image.png`
- Include size in filename if multiple sizes: `logo-small.svg`, `logo-large.svg`

### Content

- kebab-case: `brand-guidelines.md`, `design-tokens.ts`
- Descriptive, not generic: `pricing-page-copy.md` not `content.md`

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Jan 19, 2026 | Initial brand guidelines created |

---

## Contact

For questions about brand usage, contact:
- **Design Team:** design@snowscrape.com (placeholder)
- **Marketing:** marketing@snowscrape.com (placeholder)

---

**This is a living document.** Brand guidelines should evolve as the product and company grow. Review quarterly and update as needed.
