---
name: Scientific Workstation Engine
colors:
  surface: '#0f131c'
  surface-dim: '#0f131c'
  surface-bright: '#353943'
  surface-container-lowest: '#0a0e17'
  surface-container-low: '#181b25'
  surface-container: '#1c1f29'
  surface-container-high: '#262a34'
  surface-container-highest: '#31353f'
  on-surface: '#dfe2ef'
  on-surface-variant: '#bdc8d1'
  inverse-surface: '#dfe2ef'
  inverse-on-surface: '#2c303a'
  outline: '#87929a'
  outline-variant: '#3e484f'
  surface-tint: '#7bd0ff'
  primary: '#8ed5ff'
  on-primary: '#00354a'
  primary-container: '#38bdf8'
  on-primary-container: '#004965'
  inverse-primary: '#00668a'
  secondary: '#4edea3'
  on-secondary: '#003824'
  secondary-container: '#00a572'
  on-secondary-container: '#00311f'
  tertiary: '#e1bfff'
  on-tertiary: '#490080'
  tertiary-container: '#ce9bff'
  on-tertiary-container: '#6400ac'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#c4e7ff'
  primary-fixed-dim: '#7bd0ff'
  on-primary-fixed: '#001e2c'
  on-primary-fixed-variant: '#004c69'
  secondary-fixed: '#6ffbbe'
  secondary-fixed-dim: '#4edea3'
  on-secondary-fixed: '#002113'
  on-secondary-fixed-variant: '#005236'
  tertiary-fixed: '#f0dbff'
  tertiary-fixed-dim: '#ddb7ff'
  on-tertiary-fixed: '#2c0051'
  on-tertiary-fixed-variant: '#6900b3'
  background: '#0f131c'
  on-background: '#dfe2ef'
  surface-variant: '#31353f'
typography:
  headline-lg:
    fontFamily: Space Grotesk
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Space Grotesk
    fontSize: 15px
    fontWeight: '600'
    lineHeight: 20px
    letterSpacing: -0.005em
  headline-sm:
    fontFamily: Space Grotesk
    fontSize: 13px
    fontWeight: '600'
    lineHeight: 18px
    letterSpacing: 0em
  body-lg:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
  body-md:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
  body-sm:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '400'
    lineHeight: 14px
  label-lg:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
  label-md:
    fontFamily: JetBrains Mono
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 14px
  label-sm:
    fontFamily: JetBrains Mono
    fontSize: 10px
    fontWeight: '400'
    lineHeight: 12px
    letterSpacing: 0.02em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  gutter: 0.25rem
  margin: 0.25rem
  space-xs: 0.125rem
  space-sm: 0.25rem
  space-md: 0.5rem
  space-lg: 0.75rem
  space-xl: 1rem
---

## Brand & Style

This design system targets atmospheric researchers, geoscientists, numerical modelers, and satellite data analysts operating in mission-critical desktop environments. The visual language balances the tactical precision of native Qt6/PyQt scientific suites (such as Panoply, Metview, and QGIS) with the optical refinement of modern computing workstations. 

The emotional tone is calm, authoritative, exact, and noise-free. Rather than relying on expressive decorative flourishes, visual authority is derived from rigorous spatial density, mathematical rhythm, sub-pixel alignments, and crisp structural borders.

The core aesthetic combines:
- **High-Density Technical Functionalism:** Tightly packed data displays, compact toolbars, nested docking panels, and zero wasted margin space.
- **Low-Contrast Tonal Architecture:** Multi-tier deep zinc and slate surfaces preventing eye strain during 12-hour analysis sessions under multi-monitor arrays.
- **Scientific Instrument Precision:** Strict 1px delineations between panels, high-contrast monospace metrics, and dedicated spectral colormap accents (Viridis, Turbo, Plasma) reserved exclusively for data representation and critical states.

## Colors

The palette is engineered around dark-adapted workstation usability. Base surfaces live in deep slate/zinc tones, ensuring that false-color scalar fields (e.g., radar reflectivity, geopotential height, ocean surface temperature) maintain maximum radiometric dynamic range without glare.

### Surface System
- **Canvas Base (`#090d16` / `#0f172a`):** Deepest ground for viewport backgrounds, canvas viewports, and dock separators.
- **Surface Level 1 (`#131c2e`):** Main application shell, window chrome, and static panel backdrops.
- **Surface Level 2 (`#1a2436`):** Active toolbars, inspectors, parameter tree panels, and tab wells.
- **Surface Level 3 (`#222f46`):** Input fields, inactive tabs, slider tracks, and nested group boxes.
- **Surface Level 4 / Hover (`#2d3d59`):** Interactive hover states, selected list items, and active drag targets.

### Semantic & Accents
- **Primary Technical Accent (`#38bdf8` - Sky Cyan):** Active docking panel headers, focused coordinate readouts, selection bounding boxes, and active scalar isolines.
- **Secondary Instrumentation (`#10b981` - Emerald Telemetry):** Data ingest indicators, calibrated status flags, nominal model runs, and validated mesh states.
- **Tertiary State (`#a855f7` - Amethyst Vector):** Secondary coordinate frames, vector field overlays, and particle advection streamlines.
- **Warning & Hazard (`#f59e0b` / `#ef4444`):** Data dropouts, invalid netCDF attributes, memory ceiling warnings, and spatial projection mismatches.

### Data Visualization Standards
Accent colors must never compete with data fields. UI chrome is strictly desaturated. Reserve multi-stop continuous palettes (Viridis: `#440154` to `#fde725`, Turbo, Jet) exclusively for viewport overlays, colorbars, and transfer-function editors.

## Typography

The typographic hierarchy prioritizes micro-legibility and scanning efficiency under dense spatial constraints:

- **Headlines (Space Grotesk):** Applied sparingly to top-level window titles, dock manager tabs, modal titles, and major dataset identifiers. Its geometric clarity creates distinct anchor points without decorative indulgence.
- **Body & Controls (Inter):** Serves as the primary operational UI face. Renders menu bars, dropdown labels, context menus, property inspector names, and tooltips with high optical fidelity at compact sizes (11px–12px).
- **Readouts & Labels (JetBrains Mono):** Mandated for all coordinates (lat/lon/alt), timestamp indices, float/int vector magnitudes, matrix indices, memory footprints, and status bar telemetry. Tabular figure alignment ensures steady readouts during live streaming data feeds.

## Layout & Spacing

Layout in this system abandons open marketing whitespace in favor of rigorous Qt-style docking panels, splitters, tool shelves, and persistent telemetry bars.

### Splitter & Dock Architecture
- **Primary Workbench Frame:** Divided into persistent horizontal chrome (Menu/Toolbar at top, Status Bar at bottom) and a flexible internal layout containing a Center Viewport (2D/3D renderer) flanked by Left/Right dual-pane inspector docks.
- **Dock Splitters:** 4px grip zones with 1px hairline rendering (`#222f46`), expanding to a 1px `#38bdf8` guide on active drag. Docks support vertical stacking, accordion folding, and tabbed grouping.
- **Spatial Rhythm:**
  - Component gap defaults to `space-xs` (2px) and `space-sm` (4px).
  - Internal panel padding strictly adheres to `space-md` (8px).
  - Canvas margin is clamped to `margin` (4px) to maximize geospatial viewport territory.
  - Toolbar button matrices use 28x28px or 24x24px bounds with 2px inter-element separation.

## Elevation & Depth

Visual hierarchy does not use diffuse blurs, dramatic drop shadows, or skeuomorphic bevels. Instead, depth is achieved purely through **structural borders and tonal stratification**:

- **Hairline Boundary Rule:** Every panel, split lane, tab well, and widget group is delineated by a crisp `1px solid rgba(255, 255, 255, 0.08)` or `1px solid #1e293b`.
- **Z-Index Layering Tiers:**
  - **Level 0 (Canvas Base):** Recessed rendering window with an inset 1px border.
  - **Level 1 (Dock Panes):** Flat tonal fill (`#131c2e`) bounded by vertical splitter borders.
  - **Level 2 (Active Groupboxes & Inspector Cards):** Raised tonal fill (`#1a2436`) with a 1px border.
  - **Level 3 (Floating Tool Palettes & Menus):** Surface fill (`#222f46`) surrounded by an opaque 1px border (`#38bdf8` at 40% opacity) and an ultra-compact ambient shadow: `0 4px 12px rgba(0, 0, 0, 0.5)`.
- **Focus & Selection Indication:** Active panels receive an immediate top or left 2px border accent in `#38bdf8`, avoiding invasive glows or spatial shifts.

## Shapes

The geometry reflects industrial desktop tooling:
- **Containers, Panels, Viewports, Menus:** Hard 0px corners or microscopic 2px corners (`roundedness: 1`), keeping adjacent grid borders parallel without awkward corner gaps.
- **Buttons, Inputs, Badges, Tabs:** Strictly 2px to 4px maximum corner radius (`rounded-sm`). 
- **Toolbars & Segmented Controls:** Flat rectangles merged via shared single-pixel divider lines, matching Qt widget construction.
- No pill shapes (`rounded-full`) are permitted; all controls express technical firmness.

## Components

### Buttons & Action Bars
- **Toolbar Buttons:** Compact 26x26px square elements. Background transparent in rest state; `#222f46` on hover; `#2d3d59` with active `#38bdf8` bottom highlight indicator when toggled on. Icons rendered at 14x14px with 1.5px stroke weight.
- **Command Buttons:** Height 24px (`space-sm` vertical, `space-md` horizontal padding). Border `1px solid #334155`. Primary confirmation actions use `#38bdf8` text on an `#0e3a5a` tint with a `#38bdf8` 1px border.

### Dual-Pane Inspectors & Property Trees
- Structured as hierarchical tree tables with alternating row shading (`#131c2e` and `#162032`).
- Row height fixed at 22px.
- Left column (Property Key) in `body-sm` (`#94a3b8`); right column (Value Editor) in `label-sm` (`#f8fafc`).
- Collapsible tree disclosure nodes use acute triangular carets (90-degree snap on open).

### Input Fields & Steppers
- Height 22px. Base background `#0f172a`, border `1px solid #1e293b`. Focus transition changes border to `#38bdf8` with no outer ring spread.
- Numeric inputs integrate micro-scrubbers (draggable label) and vertical increment/decrement arrows aligned to the right edge. Text is strictly right-aligned for floats and integers.

### Selection Controls (Checkboxes & Radios)
- Checkboxes: 12x12px square, 1px radius. Checked state fills with `#38bdf8` featuring a sharp white checkmark.
- Radio buttons: 12x12px circle with a centered 4px filled dot when selected.

### Docking Tabs & Panel Headers
- Panel headers have a fixed 24px height, background `#1a2436`, text in `headline-sm` uppercase (10px, tracking wide).
- Dock tabs sit flush above or below viewports with active tabs rendered in `#131c2e` with a top 2px `#38bdf8` indicator line. Inactive tabs use `#0f172a` with dim text (`#64748b`).

### Colormap Transfer Function Widget
- Dedicated horizontal spectral strip (height 16px) bounded by 1px border. Supports draggable gradient stop handles (triangular 8px cursors) along its bottom edge.
- Displays dynamic min/max value indicators in `label-sm` immediately flanking the spectrum.

### Status Bar & Telemetry Strip
- Persistent 20px bottom dock strip. Segmented into fixed-width cells via `1px solid #1e293b`.
- Houses real-time cursor coordinates (e.g., `LAT: 42.3601° N  LON: 71.0589° W`), current map scale/projection code (`EPSG:4326`), rendered FPS counter, and memory buffer usage gauge.