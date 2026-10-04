# GUI Architecture & Implementation

## Overview
Implemented the full PyQt6 desktop GUI based on the prototype layout in [`gui_base.html`](file:///home/xotem/projects/xotplot/gui_base.html), including dark and light theme switching.

## Layout & Components
1. **Header & Navigation Menus**:
   - Menu bar (`File`, `Edit`, `View`, `Projection`, `Tools`, `Help`).
   - `View -> Dark Mode` (shortcut `Ctrl+T`) toggles between dark and light themes dynamically.
2. **Main Toolbar**:
   - Quick actions (`Open Data`, `Preview`, `Render`, `Toggle Light/Dark`).
   - Backend and DPI telemetry display.
3. **Left Dock (`Data & Dimensions`)**:
   - Active ingest file card and resolution info (`GFS_Global_0p25deg_...`).
   - Variables list by physics (`HGT_500hPa`, `UGRD/VGRD_850`, etc.).
   - Vertical isobaric slice selector buttons (`SFC`, `850`, `700`, `500`, `250`, `100`).
4. **Center Workspace (`ViewportWidget`)**:
   - Mini-toolbar: Pan, Zoom, Reset Extent, Probe, Export Fig.
   - Live scientific SVG viewport rendered via `QSvgWidget` using the synoptic chart specifications.
   - Spectral Turbo colormap gradient strip with geopotential height level indicators.
   - Scrubbing dual-stage slider for forecast lead time (`sliderMoved` -> preview, `sliderReleased` -> commit).
5. **Right Dock (`Configuration & Layers`)**:
   - **Cartopy Projection Tab**: Projection selector dropdown (`LambertConformal`, `PlateCarree`, etc.), central lon/lat coordinates, render mode (`contourf` vs `pcolormesh`), and shapefile feature layer toggles.
   - **CLI Script Tab**: Synchronized command pipeline script preview.
6. **Status Bar**:
   - Cursor geo-coordinates telemetry (`LAT / LON`) and processing state indicators.

## Running and Testing
See commands in the testing section:
- Launch GUI: `uv run xotplot`
- Verification script: `uv run python -c "..."`
