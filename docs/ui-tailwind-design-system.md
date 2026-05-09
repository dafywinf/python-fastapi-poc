# UI Design System: PrimeVue + Tailwind v4 Pass-Through

## Overview

This document explains the approach used to migrate the frontend from PrimeVue's
built-in theme system to a fully custom Tailwind v4 design system, while keeping
PrimeVue as the component library.

The key insight is that PrimeVue supports an `unstyled` mode where it renders
completely bare HTML with no CSS of its own. You then supply all classes via a
**pass-through (PT)** configuration object. Combined with Tailwind v4's `@theme`
design token system, this gives you full visual control without replacing any
component logic or accessibility behaviour.

---

## Architecture

```
style.css (@theme)          ← single source of truth for all brand values
    │
    ├── generates Tailwind utilities (bg-app-red, text-app-muted, …)
    │
primevue-pt.ts              ← maps PrimeVue internal slots → Tailwind classes
    │
    └── referenced by app.use(PrimeVue, { unstyled: true, pt: primevuePt })
```

Templates remain unchanged — `<DataTable>`, `<Button>`, `<Tag>` etc. are still
PrimeVue components. Only the emitted CSS changes.

---

## Part 1: Tailwind v4 Design Tokens (`style.css`)

Tailwind v4 introduces `@theme`, a CSS block where you declare custom properties
that are automatically turned into full utility sets.

```css
@theme {
  --color-app-red: #E2001A;
}
```

This single declaration generates `bg-app-red`, `text-app-red`, `border-app-red`,
`ring-app-red`, `fill-app-red`, and every other colour utility variant — with no
plugin or config file needed.

### Token categories

| Category | Tokens | Description |
|---|---|---|
| Typefaces | `--font-sans`, `--font-data` | Body (Source Sans 3) and monospace (JetBrains Mono) |
| Brand accents | `app-red`, `app-teal`, `app-amber` | Invariant across light/dark — always vivid |
| Shell | `app-dark` | Navbar + sidebar background, never inverts |
| Adaptive surfaces | `app-surface`, `app-card`, `app-border`, `app-text`, `app-muted` | Redefined under `[data-theme="dark"]` |

### Dark mode

Adaptive tokens are declared with light defaults and then overridden:

```css
@theme {
  --color-app-surface: #F4F5F7;   /* light default */
  --color-app-card:    #FFFFFF;
}

[data-theme='dark'] {
  --color-app-surface: #0A0B0E;   /* dark override */
  --color-app-card:    #14181D;
}
```

Because Tailwind v4 resolves utilities to CSS custom properties at render time,
`bg-app-surface` automatically reflects the active theme — no `dark:` prefix
needed in templates for surface colours.

Dark mode is toggled by `useDarkMode.ts`, which sets `data-theme="dark"` on
`<html>` and persists the choice to `localStorage` via `usePersistedRef.ts`.

### Font loading

Google Fonts is loaded in `index.html`:

```html
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Source+Sans+3:ital,wght@0,200..900;1,200..900&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet" />
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200" rel="stylesheet" />
```

`--font-sans` in `@theme` then picks up Source Sans 3 and applies it globally.
Material Symbols Outlined provides icons via `<span class="material-symbols-outlined">`.

---

## Part 2: PrimeVue Pass-Through (`primevue-pt.ts`)

### What is pass-through?

Every PrimeVue component exposes named slots for its internal DOM elements. For
example, `DataTable` exposes `root`, `table`, `thead`, `headerRow`, `headerCell`,
`tbody`, `row`, `bodyCell`, and so on. The PT object maps each slot name to a
`class` string (or a function that returns one based on props/context).

### Enabling unstyled mode

In `main.ts`:

```ts
import { primevuePt } from './primevue-pt'

app.use(PrimeVue, { unstyled: true, pt: primevuePt })
```

`unstyled: true` strips all PrimeVue CSS. Without a PT config the components would
render as bare, unstyled HTML. The `pt` object re-applies classes from your own
design system.

### Static vs dynamic slots

Static slots receive a plain object:

```ts
datatable: {
  headerCell: {
    class: 'px-4 py-2 text-[11px] font-bold text-gray-500 uppercase tracking-[0.05em] bg-app-border/20 border-b border-app-border',
  },
}
```

Dynamic slots receive a function that takes `{ props, context }` and returns the
class object. This is used for components that change appearance based on their
own props (e.g. `severity` on `Button` and `Tag`, active page on `Paginator`):

```ts
button: {
  root: (({ props }) => ({
    class: [
      'inline-flex items-center font-semibold cursor-pointer transition-colors rounded-sm uppercase tracking-wider',
      props['severity'] === 'danger'
        ? 'bg-transparent text-app-red border-app-red/40 hover:bg-red-50'
        : 'bg-app-red text-white hover:opacity-90',
    ],
  })) as DynCls,
},
```

### Components covered

| PrimeVue component | PT key | Notes |
|---|---|---|
| `Button` | `button` | Severity variants: primary (red), secondary (muted), danger |
| `DataTable` | `datatable` | Full table structure — thead, row hover, empty state |
| `Column` | `column` | headerCell + bodyCell alignment |
| `Dialog` | `dialog` | Modal, mask overlay, header/footer layout |
| `InputText` | `inputtext` | Focus ring uses `app-red` |
| `Textarea` | `textarea` | Same as InputText, adds `resize-y` |
| `Select` | `select` | Dropdown overlay, option hover |
| `Checkbox` | `checkbox` | Box + icon |
| `ProgressSpinner` | `progressspinner` | Spin animation, `stroke-app-red` |
| `Tag` | `tag` | Severity variants: primary, secondary, success, danger, warn, info |
| `Paginator` | `paginator` | Active page = `bg-app-red text-white` |
| `Toast` | `toast` | Bottom-right, severity-coloured backgrounds |

---

## Part 3: Navigation Restructure

### Before

- Navbar contained all navigation links (Routines, History, Users) alongside the
  brand name and auth controls.
- Sidebar was light grey (`bg-slate-50`), contained only Routines and History,
  used Unicode glyphs as icons, and had an `indigo` active state.
- No dark mode support anywhere.

### After

**Navbar** is now branding + identity only:
- Logo block: red square icon + "Operations / Control" two-line wordmark
- Red accent bar as a visual separator
- Dark mode toggle (sun/moon icon via Material Symbols)
- User email + Sign Out / Sign in with Google buttons (raw `<button>` — no PrimeVue)
- No navigation links

**Sidebar** owns all navigation:
- Always-dark (`bg-app-dark`) to match the navbar shell
- Four links: Dashboard, Routines, History, Users
- Material Symbols icons (replacing Unicode glyphs)
- Active state: `border-l-2 border-l-app-red bg-white/8` — red left-border highlight
- Version string in a fixed footer area at the bottom

### Why the navbar buttons are raw HTML

Simple two-state controls (Sign In / Sign Out) do not benefit from PrimeVue's
component machinery. Replacing them with `<button>` elements avoids the PT
indirection for code that will never need severity variants, loading states, or
icons. More complex interactive controls (dialogs, tables, forms) remain as
PrimeVue components because the PT system covers them uniformly.

---

## Applying this to another app

The portable pieces are, in order:

1. **`style.css`** — copy the `@theme` block and `[data-theme="dark"]` override.
   Adjust colour values to match your brand. The token names (`app-red`, `app-surface`,
   etc.) are referenced everywhere else so rename consistently if you change them.

2. **`index.html`** — add the Google Fonts `<link>` tags for your chosen typefaces
   and for Material Symbols if you want the same icon set.

3. **`usePersistedRef.ts`** + **`useDarkMode.ts`** — copy as-is. No dependencies
   beyond Vue 3.

4. **`primevue-pt.ts`** — copy and verify that every PrimeVue component your app
   uses has an entry. The type aliases (`Cls`, `DynCls`) are self-contained.
   Update `main.ts` to pass `{ unstyled: true, pt: primevuePt }`.

5. **`AppNavbar.vue`** + **`AppSidebar.vue`** — adapt structure and links to your
   app's routes. The Tailwind classes reference only the tokens from step 1.

6. **`App.vue`** — change the `<main>` background from `bg-white` to `bg-app-surface`.

> **To retheme entirely:** edit the `@theme` block in `style.css` only. Every
> utility class throughout the app (`bg-app-red`, `border-app-border`, etc.)
> resolves at render time from those CSS custom properties, so the entire UI
> updates from a single file.
