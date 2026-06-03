# Landing Page Redesign Plan — 光影圆环动态效果

> **Goal:** Redesign the project landing page to match the reference image style (dark theme, glowing arc, glassmorphism card) with an animated light-flow ring on the left side.

---

## 1. Design Analysis

### Reference Image Characteristics
- **Background:** Deep black (`#000000` to `#0a0a0f`) with subtle noise texture
- **Left Element:** Large glowing arc/ring with soft blue-white light, ethereal and atmospheric
- **Right Content:** Glassmorphism card with frosted glass effect, subtle border, dark translucent background
- **Typography:** Clean sans-serif, high contrast white text on dark, muted gray for secondary text
- **Color Palette:** Monochromatic dark with cool blue-white accent glow
- **Mood:** Futuristic, premium, minimal, atmospheric

### Current Page Analysis
- Current: Light theme (slate-50 background), standard dashboard layout
- Target: Dark theme landing page with dramatic visual element

---

## 2. Technical Architecture

### Tech Stack
- **Framework:** Next.js 16 + React 19 + Tailwind CSS v4
- **Animation:** Framer Motion for UI transitions + Canvas 2D/WebGL for ring animation
- **Fonts:** Keep Noto Sans SC for Chinese, add a distinctive display font for English headings

### File Structure

| File | Action | Description |
|------|--------|-------------|
| `web-dashboard/src/app/page.tsx` | **Rewrite** | Landing page with dark theme, ring animation, glass card |
| `web-dashboard/src/app/globals.css` | **Modify** | Add dark theme CSS variables, ring animation keyframes, noise texture |
| `web-dashboard/src/components/GlowRing.tsx` | **Create** | Canvas-based animated light-flow ring (3 modes) |
| `web-dashboard/src/components/GlassCard.tsx` | **Create** | Glassmorphism card component |
| `web-dashboard/src/app/layout.tsx` | **Modify** | Update metadata, add dark theme body class |

---

## 3. Implementation Tasks

### Task 1: Update Global Styles (Dark Theme Foundation)

**File:** `web-dashboard/src/app/globals.css`

**Changes:**
- Add dark theme color variables (background: `#000000`, surface: `rgba(255,255,255,0.03)`, etc.)
- Add CSS noise texture overlay
- Add glow ring keyframe animations
- Keep existing prose styles but add dark mode variants

```css
/* Dark theme overrides */
@theme inline {
  --color-bg-dark: #000000;
  --color-surface-glass: rgba(255, 255, 255, 0.03);
  --color-border-glass: rgba(255, 255, 255, 0.08);
  --color-glow-primary: #a5b4fc;
  --color-glow-secondary: #6366f1;
  --color-text-primary-dark: #f8fafc;
  --color-text-secondary-dark: #94a3b8;
  --color-text-muted-dark: #475569;
}
```

---

### Task 2: Create GlowRing Component (Canvas Animation)

**File:** `web-dashboard/src/components/GlowRing.tsx`

**Requirements:**
- Canvas 2D rendering for smooth 60fps animation
- 3 animation modes:
  1. **Flow** — Continuous light traveling along the ring path (default)
  2. **Pulse** — Rhythmic breathing glow effect
  3. **Orbit** — Multiple light particles orbiting the ring
- Configurable: color, speed, intensity, mode
- Responsive: scales with container size
- Performance: uses `requestAnimationFrame`, cleans up on unmount

**Visual Spec:**
- Ring shape: Large partial arc (roughly 240°), positioned on left side
- Glow: Soft Gaussian blur, cool blue-white gradient (`#c7d2fe` → `#6366f1`)
- Core: Brighter center line with softer outer halo
- Background: Transparent (relies on page background)

---

### Task 3: Create GlassCard Component

**File:** `web-dashboard/src/components/GlassCard.tsx`

**Requirements:**
- Frosted glass effect using `backdrop-blur-xl`
- Semi-transparent dark background (`rgba(255,255,255,0.03)`)
- Subtle border (`rgba(255,255,255,0.08)`)
- Optional inner glow on hover
- Supports: title, subtitle, children content

---

### Task 4: Rewrite Landing Page

**File:** `web-dashboard/src/app/page.tsx`

**Layout Structure:**
```
┌─────────────────────────────────────────────────────────────┐
│  [Top Bar] Logo + Nav (minimal, transparent)               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌──────────┐                              ┌──────────┐   │
│   │          │                              │          │   │
│   │  ◯═══    │         ~40% gap            │  Glass   │   │
│   │  Glow    │                              │  Card    │   │
│   │  Ring    │                              │  Content │   │
│   │          │                              │          │   │
│   └──────────┘                              └──────────┘   │
│                                                             │
│   [Mode Selector: Flow | Pulse | Orbit]                    │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  [Footer] Minimal copyright / links                        │
└─────────────────────────────────────────────────────────────┘
```

**Content for Glass Card:**
- Title: "播客笔记" (large, bold)
- Subtitle: "自动化内容提炼" (muted)
- Description: Brief value proposition
- CTA Button: "开始使用" (primary action)
- Secondary links: 功能介绍 / 文档

**Responsive Behavior:**
- **Desktop (≥1024px):** Side-by-side layout, ring on left, card on right
- **Tablet (768-1023px):** Ring becomes background element (faded), card centered
- **Mobile (<768px):** Ring hidden or minimal top decoration, card full-width stacked

---

### Task 5: Update Layout

**File:** `web-dashboard/src/app/layout.tsx`

**Changes:**
- Update metadata title to match landing page branding
- Ensure body supports dark theme (black background)
- Keep font configuration

---

### Task 6: Build & Verify

**Steps:**
1. Run `npm run build` to verify TypeScript compilation
2. Run `npm run dev` and test in browser
3. Verify:
   - Ring animation runs at 60fps (check DevTools Performance)
   - All 3 modes switch correctly
   - Responsive layout works on all breakpoints
   - Glass card renders with proper backdrop blur
   - No layout shift on page load

---

## 4. Design Specifications

### Color Palette (Dark Theme)
| Token | Value | Usage |
|-------|-------|-------|
| `bg-primary` | `#000000` | Page background |
| `bg-surface` | `rgba(255,255,255,0.03)` | Card background |
| `border-glass` | `rgba(255,255,255,0.08)` | Card border |
| `glow-core` | `#c7d2fe` | Ring bright center |
| `glow-mid` | `#818cf8` | Ring middle gradient |
| `glow-outer` | `#4f46e5` | Ring outer fade |
| `text-primary` | `#f8fafc` | Headings |
| `text-secondary` | `#94a3b8` | Body text |
| `text-muted` | `#475569` | Captions |
| `accent` | `#6366f1` | Buttons, links |

### Typography Scale
| Element | Size | Weight | Color |
|---------|------|--------|-------|
| Logo | 18px | 700 | `text-primary` |
| H1 (Title) | 48px | 800 | `text-primary` |
| H2 (Subtitle) | 20px | 400 | `text-secondary` |
| Body | 16px | 400 | `text-secondary` |
| Caption | 14px | 400 | `text-muted` |
| Button | 16px | 600 | white on `accent` |

### Spacing
- Page padding: `px-6 md:px-12 lg:px-20`
- Card max-width: `480px`
- Ring container: `60vw` width on desktop, centered
- Gap between ring and card: `auto` (flex justify-between)

### Animation Specs
| Element | Animation | Duration | Easing |
|---------|-----------|----------|--------|
| Page load | Fade in + slide up | 0.8s | `cubic-bezier(0.16, 1, 0.3, 1)` |
| Ring glow | Continuous flow | 4s loop | linear |
| Card hover | Border glow intensify | 0.3s | ease-out |
| Mode switch | Cross-fade | 0.5s | ease-in-out |
| Button hover | Scale 1.02 + glow | 0.2s | ease-out |

---

## 5. Acceptance Criteria

- [ ] Page background is pure black with subtle noise texture
- [ ] Left side features a large glowing arc with smooth light-flow animation
- [ ] 3 animation modes (Flow/Pulse/Orbit) are selectable and functional
- [ ] Animation maintains ≥30fps (target 60fps) on modern browsers
- [ ] Right side features a glassmorphism card with frosted effect
- [ ] Card contains: title, subtitle, description, CTA button
- [ ] Responsive: desktop side-by-side, tablet stacked with faded ring, mobile card-only
- [ ] All text uses Noto Sans SC, proper Chinese rendering
- [ ] Build passes without TypeScript errors
- [ ] No console warnings or errors

---

## 6. Summary

This redesign transforms the current light-themed dashboard into a dramatic dark landing page inspired by the reference image. The key visual element is a Canvas-rendered glowing ring with 3 animation modes, paired with a glassmorphism content card. The design prioritizes atmosphere and visual impact while maintaining usability and responsiveness.

**Estimated effort:** 6 tasks, ~2-3 hours.
**Key technical decisions:**
- Canvas 2D for ring animation (performance, control)
- CSS backdrop-filter for glass effect (native browser support)
- Framer Motion for UI transitions (consistent with existing stack)
- Tailwind CSS v4 theme extension for dark color tokens
