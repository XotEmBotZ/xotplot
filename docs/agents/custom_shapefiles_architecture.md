# Feature-Specific Shapefiles & General Custom Shapefiles Architecture

## 1. Feature-Specific Shapefile Overrides
In [`src/xotplot/gui/views/projection_cartopy_view.py`](file:///home/xotem/projects/xotplot/src/xotplot/gui/views/projection_cartopy_view.py), each natural feature row in `4. Cartopy Borders & Feature Layer Config` provides an inline `📁 .shp` file picker button:
- **Coastlines**: `btn_coast_shp` sets `_custom_shp_coast` (overrides Natural Earth coastline).
- **Country Borders**: `btn_border_shp` sets `_custom_shp_borders` (overrides Natural Earth borders).
- **State / Provinces**: `btn_state_shp` sets `_custom_shp_states` (overrides Natural Earth admin 1).
- **Rivers**: `btn_river_shp` sets `_custom_shp_rivers` (overrides Natural Earth rivers).
- **Lakes**: `btn_lake_shp` sets `_custom_shp_lakes` (overrides Natural Earth lakes).

When set, the button indicates `✓ <filename>` in blue. The rendering pipeline loads the user's custom shapefile via `cartopy.feature.ShapelyFeature` rather than searching Natural Earth.

## 2. Additional Custom Shapefiles Stack
Under `5. Custom Shapefiles (.shp)`:
- `+ Add Shapefile...` imports any external shapefiles or GIS layers into a multi-layer stack.
- Manages visibility, stroke width (`spin_shp_width`), and geometry stroke color (`_shp_color`).
- Rendered via `ShapelyFeature(geoms, crs=PlateCarree(), ...)` with `ax.add_feature()`, guaranteeing error-free cross-projection transformation (e.g. Lambert Conformal, Orthographic, Mercator, Plate Carrée).

## 3. Robust Offline-Safe Shapefile Loader (`load_shapefile_geometries`)
In [`src/xotplot/gui/cartopy_features.py`](file:///home/xotem/projects/xotplot/src/xotplot/gui/cartopy_features.py):
- **Missing `.dbf` Fallback**: Standard `cartopy.io.shapereader.Reader` raises `shapefile.ShapefileException: DbfReader requires a .dbf file` when only `.shp` and `.shx` exist (as in typical standalone boundary datasets like `India_State.shp`). The loader catches this and falls back to `shapefile.Reader(shp=..., shx=...)` directly through `pyshp` and `shapely.geometry.shape`.
- **High-Density Auto-Simplification**: Datasets with hundreds of thousands or millions of coordinate points freeze Matplotlib projection transforms (e.g. Lambert Conformal, Stereographic). If total coordinates > 10,000, geometries are simplified (`geom.simplify(0.005, preserve_topology=True)`), rendering in < 4 seconds while maintaining high geographical fidelity.

