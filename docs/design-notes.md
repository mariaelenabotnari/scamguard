# Scamguard UI Design Specification & Token System

This document defines the visual architecture, colour system, typography, spacing, iconography, and data visualization specifications for the **Scamguard** dashboard. All tokens map directly into `tailwind.config.js`.

---

## 1. Layout & Grid Structure

The application uses a **three-column desktop shell** housed inside an elevated workspace container:

1. **Left Navigation Sidebar (`240px` fixed width on desktop, collapsible to `72px` on tablet, drawer on mobile)**:
   - **Background**: Pure white (`#FFFFFF`).
   - **Brand Header**: Geometric indigo emblem (`#2D317A` and `#5A60B5`) centered at the top with brand title **Scamguard** (`14px`, `font-semibold`, `#2D317A`).
   - **Primary Navigation List**: Vertical stack with `20px` vertical spacing, left-aligned Font Awesome icons (`16px`), and labels (`14px`, `#94A3B8` inactive, `#2D317A` active with `font-semibold`).
   - **Sidebar Toggle Button**: Circular white button (`28px × 28px`, subtle shadow, `fa-chevron-left`) anchored on the right border edge of the sidebar.
   - **Bottom Mini Widget ("Statics" / Collection Pulse)**: Rounded light card (`#F4F6FB`, `rounded-2xl`, `p-4`) with header, `fa-ellipsis` button, and a 7-bar vertical mini chart showing `Max` and `Min` collection/activity levels.

2. **Center Main Workspace (`flex-1`, min-width `0`, background `#F5F7FB`, padding `24px–32px`)**:
   - **Top Bar (`56px` height)**:
     - Left: Global search input with `fa-magnifying-glass` icon and muted placeholder (`#94A3B8`).
     - Right: White rounded timestamp/status pill (`#FFFFFF`, `rounded-xl`, `px-4 py-2`, `fa-clock` in `#43489B`), language switcher (`EN` / `RO` / `RU` with `fa-chevron-down`), and notification bell (`fa-bell`) with unread badge dot.
   - **Hero / Overview Banner Card**:
     - Full-width rounded card (`#E5E9F8`, `rounded-2xl`, `px-8 py-6`) with headline (`26px`, `font-bold`, `#353A85`), subtitle (`14px`, `#7E86A8`), and decorative right-side vector graphic.
   - **Primary Activity Timeline Card**:
     - Rounded container (`#EBF0FA`, `rounded-2xl`, `p-6`).
     - Header with title (`17px`, `font-bold`, `#353A85`), subtitle (`12px`, `#8C93B0`), and a pill-shaped range switcher (`#474B9E` container with `#FFFFFF` active pill for `24h`, `7d`, `30d`).
     - Smooth spline area/line chart with vertical guide stems, circular top anchor nodes, interactive floating callout card (`#D3D9F2`, `rounded-2xl`), and bottom axis labels.
   - **4-Column Bottom KPI Stat Grid (`grid-cols-1 sm:grid-cols-2 xl:grid-cols-4`, gap `20px`)**:
     - Each card (`#FFFFFF`, `rounded-2xl`, `p-4`) displays a `44px × 44px` pastel rounded-xl icon box on the left and stacked label, primary metric value, and trend delta (`+33.45%`) on the right.

3. **Right Context & Summary Panel (`300px` fixed width on large screens, stacks below on smaller screens)**:
   - **Background**: Soft lavender-periwinkle (`#E3E7F7`).
   - **User / Role Header**: Avatar (`48px` rounded-full with white border), user full name (`16px`, `font-bold`, `#2D317A`), role subtitle (`12px`, `#7E86A8`), and quick drawer/settings icon (`fa-bars-staggered`).
   - **Stacked Quick-Metric Action Cards (3 cards)**:
     - White cards (`#FFFFFF`, `rounded-2xl`, `p-4`) with metric title (`12px`, `#94A3B8`), bold count (`18px`, `#2D317A`), and right-aligned action button (`#F4F6FB`, `rounded-lg`, `fa-chevron-right`).
   - **7-Day Activity Strip**:
     - Horizontal day selector (`Mo`–`Su`) with active day highlighted in a vertical indigo pill (`#474B9E`, `#FFFFFF` text, dot indicator).
   - **Audit / Coordination Score Gauge**:
     - Header with section title (`14px`, `font-bold`, `#2D317A`) and removable period pill (`#CFD5EE`, `rounded-full`, `fa-xmark`).
     - Radial donut gauge (`75%`) with thick indigo arc (`#474B9E`), soft periwinkle track (`#CFD5EE`), inner white ring, and centered metric + caption.
     - Bottom linear progress bar (`38%`) for secondary risk/coverage ratio.

---

## 2. Colour Palette (Hex Tokens)

### Surfaces & Backgrounds
- `bg-canvas`: `#E6EAF2` (outer viewport background)
- `bg-app`: `#F5F7FB` (center main workspace surface)
- `bg-sidebar`: `#FFFFFF` (left sidebar surface)
- `bg-panel`: `#E3E7F7` (right summary panel surface)
- `bg-banner`: `#E5E9F8` (hero greeting banner & soft indigo cards)
- `bg-chart`: `#EBF0FA` (timeline chart card surface)
- `bg-tooltip`: `#D3D9F2` (floating chart callout surface)
- `bg-muted`: `#F3F5FA` (subtle button & mini-widget background)

### Brand & Primary Accents
- `brand-900` / `ink-primary`: `#2D317A` (deep navy-indigo for primary headings, numbers, active icons)
- `brand-700` / `primary`: `#474B9E` (primary interactive indigo: chart line, active pills, radial gauge, toggles)
- `brand-500` / `primary-light`: `#6C72C9` (secondary chart accents, hover states)
- `brand-200` / `track`: `#CFD5EE` (progress tracks, subtle borders, pill tags)
- `brand-100`: `#E6E8F8` (lavender icon badge tint)

### Typography Colours
- `text-primary`: `#2D317A` (headings, KPI values, active nav)
- `text-secondary`: `#5A607F` (body copy, table cells)
- `text-muted`: `#8C93B0` (subtitles, axis labels, inactive nav items, timestamps)

### Status & KPI Pastel Tints
- **Low Risk / Info Cyan**:
  - Surface: `#E1F3F7`
  - Text / Icon: `#1E6B7B`
- **Medium Risk / Warning Peach**:
  - Surface: `#FDF0E1`
  - Text / Icon: `#B45309`
- **High Risk / Danger Rose**:
  - Surface: `#FCE8E9`
  - Text / Icon: `#BE123C`
- **Success / Verified Emerald**:
  - Surface: `#E3F6EC`
  - Text / Icon: `#15803D`

---

## 3. Typography

- **Font Family**: `'Plus Jakarta Sans'` with `'Inter'` fallback (Google Fonts, geometric sans-serif with clean tabular numerals).
- **Scale & Weights**:
  - **Hero Title / Gauge Value**: `26px–28px` (`1.625rem–1.75rem`), weight `700` (`font-bold`), tracking `-0.02em`.
  - **Card Metric Value**: `20px` (`1.25rem`), weight `700` (`font-bold`), colour `#2D317A`.
  - **Section Heading**: `16px–18px` (`1rem–1.125rem`), weight `700` (`font-bold`), colour `#2D317A`.
  - **Body / Nav Item**: `14px` (`0.875rem`), weight `500` (`font-medium`) or `600` (`font-semibold` when active).
  - **Caption / Label / Trend**: `11px–12px` (`0.6875rem–0.75rem`), weight `500` (`font-medium`), colour `#8C93B0`.

---

## 4. Spacing, Border Radius & Shadows

- **Border Radius**:
  - Outer App Shell: `28px` (`rounded-3xl`)
  - Primary Cards (Banner, Chart, KPI Cards, Right Panel Cards): `18px–20px` (`rounded-2xl`)
  - Icon Badges & Pill Controls: `12px` (`rounded-xl`)
  - Small Action Chevrons & Tags: `8px` (`rounded-lg`)
- **Spacing**:
  - Main workspace padding: `28px` (`p-7`)
  - Card internal padding: `16px` (`p-4`) for compact KPI cards, `24px` (`p-6`) for chart and banner cards
  - Grid gap: `20px` (`gap-5`)
- **Shadows**:
  - `shadow-shell`: `0 24px 60px -15px rgba(45, 49, 122, 0.12)`
  - `shadow-card`: `0 6px 20px -4px rgba(45, 49, 122, 0.05)`
  - `shadow-pill`: `0 2px 8px rgba(45, 49, 122, 0.08)`

---

## 5. Icons (Font Awesome Mapping)

All icons across the application use **Font Awesome** (`@fortawesome/react-fontawesome` + `@fortawesome/free-solid-svg-icons`):

| UI Element | Scamguard Role | Font Awesome Icon (`free-solid-svg-icons`) |
|---|---|---|
| Dashboard nav | Overview Dashboard | `faGaugeHigh` |
| Profile / Channels nav | Channels & Watchlist | `faSatelliteDish` / `faUser` |
| Utilities / Clusters nav | Coordinated Clusters | `faLayerGroup` / `faBriefcase` |
| Settings nav | Admin & Threshold Settings | `faGear` |
| Messages nav | Messages & Search | `faEnvelope` |
| Analytics nav | Risk Ranking & Analytics | `faChartPie` |
| Integrations nav | Alerts & Data Export | `faShareNodes` |
| Sidebar toggle | Collapse / Expand Sidebar | `faChevronLeft` / `faChevronRight` |
| Widget menu | Card actions | `faEllipsis` |
| Search bar icon | Global search | `faMagnifyingGlass` |
| Status pill icon | Collection timestamp | `faClock` |
| Dropdown indicator | Language / range selector | `faChevronDown` |
| Notification icon | Active alerts indicator | `faBell` |
| KPI 1 icon | Watched Channels | `faHandPointer` |
| KPI 2 icon | Messages Today | `faClock` |
| KPI 3 icon | Active Clusters | `faUsers` |
| KPI 4 icon | High-Risk Channels | `faCirclePlay` |
| Right panel menu | Context drawer options | `faBarsStaggered` |
| Summary card action | Drill down | `faChevronRight` |
| Filter tag dismiss | Clear period filter | `faXmark` |

---

## 6. Charts, Tables & Data Requirements

1. **Main Activity Timeline Chart (Recharts `ResponsiveContainer` + `AreaChart` / `LineChart`)**:
   - **Visuals**: Smooth `monotone` spline in `#474B9E`, vertical reference stems with top circle indicators, highlighted active point with floating callout card.
   - **Data needed**: Time bucket label (`24h` hourly, `7d` daily, `30d` daily), `messagesCount`, `clustersCount`, and peak callout annotation (`timestamp`, `headlineMetric`, `label`).
2. **Bottom-Left "Statics" Mini Bar Chart**:
   - **Visuals**: 7 vertical rounded bars of varying heights (`#3B3F8C` for peak bars, `#9BA2D6` for regular bars) with `Max` and `Min` labels.
   - **Data needed**: Array of recent interval counts (`label`, `value`, `isMax`, `isMin`).
3. **Right-Panel Radial Gauge ("Audit" / Coordination Risk / Narrative Coverage)**:
   - **Visuals**: Circular SVG or Recharts `RadialBarChart` showing percentage (`0–100%`) with inner white border ring and bottom horizontal progress bar.
   - **Data needed**: Primary percentage (`75%`), label (`Reviews` / `Evaluated`), secondary percentage (`38%`), and secondary label (`High-Risk Share`).
4. **Domain Tables & Lists (Risk Ranking, Clusters List, Channel Compare, Alerts)**:
   - Styled with `rounded-2xl` surfaces, `#2D317A` headings, `#5A607F` cells, pastel status badges (`Low`, `Medium`, `High`), and inline explanation blocks.
