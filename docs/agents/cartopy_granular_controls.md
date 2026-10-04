# Granular Cartopy Borders & Custom Shapefiles Configuration

## Overview
Added full granular control over Cartopy vector features, border stroke styles, natural earth resolutions, graticule parameters, and custom `.shp` shapefile import into [`ProjectionCartopyView`](file:///home/xotem/projects/xotplot/src/xotplot/gui/views/projection_cartopy_view.py).

## Granular Configuration Options Added

### 1. Natural Earth Feature Scale
- **Resolution Levels**: `110m (Coarse)`, `50m (Medium - Default)`, `10m (High-Res)`.

### 2. Coastline Controls
- Toggle: `Coastlines` checkbox.
- Stroke Width: `spin_coast_width` (0.2 to 5.0).
- Color Picker: `btn_coast_col` (via `QColorDialog`).

### 3. Country Borders
- Toggle: `Country Borders` checkbox.
- Line Style: `Dashed (--)`, `Solid (-)`, `Dotted (:)`.
- Color Picker: `btn_border_col`.

### 4. State & Province Subdivisions
- Toggle: `State / Provinces` checkbox (admin level 1).
- Stroke Width: `spin_state_width` (0.2 to 3.0).
- Line Style: Dotted line formatting.
- Color Picker: `btn_state_col`.

### 5. Hydrography (Rivers & Lakes Outlines)
- Toggle: `Rivers` & `Lakes Outline` checkboxes.
- Stroke Widths: `spin_river_width` & `spin_lake_width`.
- Color Pickers: `btn_river_col` & `btn_lake_col`.

### 6. Custom Shapefiles (.shp) Import Engine
- `+ Add Shapefile...` button opens file dialog accepting `.shp` and `.gpkg`.
- Loaded shapefile manager table showing active loaded shape layers.
- Remove button to detach layers.
- Custom shapefile stroke width spinner (`spin_shp_width`).
- Custom shapefile color picker (`btn_shp_color`).
- Renders via `cartopy.io.shapereader.Reader` with `ax.add_geometries()` at `zorder=4`.

### 7. Graticules & Gridlines Inspector
- Draw Gridlines and Coordinate Labels checkboxes.
- Grid styles: `Dashed (--)`, `Solid (-)`, `Dotted (:)`.
- Grid spacing: `Lon Step (°)` and `Lat Step (°)` (0.5° to 60.0°).
- Grid Color Picker & Alpha Transparency Slider (10% to 100%).
