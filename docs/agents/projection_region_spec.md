# Projection and Region Spec Architecture

This document describes the Pydantic schema architecture used for saving, loading, and validating configurations for the **Projection & Region View** and the overall `PlotSpec` in `xotplot`.

## Core Philosophy Adherence
- **Fail-Fast**: Type hints and Pydantic constraints validate geographic bounds (`-180 <= lon <= 180`, `-90 <= lat <= 90`, `gt=0` line widths) and strict string literals without silent fallbacks.
- **Simple-Only & Least-Code**: Direct JSON serialization via Pydantic v2 `model_dump_json` and `model_validate_json`.
- **Constants Integration**: Default colors and presets are bound directly to `src/xotplot/constants.py`.

## Schema Models (`src/xotplot/spec.py`)

- [`ExtentSpec`](file:///home/xotem/projects/xotplot/src/xotplot/spec.py): Geographic bounds `(west, east, south, north)` with bounding checks.
- [`ProjectionSpec`](file:///home/xotem/projects/xotplot/src/xotplot/spec.py): CRS selection (`LambertConformal`, `PlateCarree`, `Mercator`, `NorthPolarStereo`, `Orthographic`, `Robinson`), central longitude, central latitude, standard parallels.
- [`FeatureLayerSpec`](file:///home/xotem/projects/xotplot/src/xotplot/spec.py): Per-feature styling (`enabled`, `color`, `linewidth`, `linestyle`, `custom_shapefile`).
- [`FeaturesSpec`](file:///home/xotem/projects/xotplot/src/xotplot/spec.py): Granular Cartopy Natural Earth features (`scale`, `coastlines`, `borders`, `states`, `rivers`, `lakes`).
- [`CustomShapefileSpec`](file:///home/xotem/projects/xotplot/src/xotplot/spec.py): Custom shapefile layer entries (`path`, `name`, `enabled`, `color`, `linewidth`).
- [`GraticuleSpec`](file:///home/xotem/projects/xotplot/src/xotplot/spec.py): Lat/lon grid line intervals, style, labels, color, and alpha transparency.
- [`RegionViewSpec`](file:///home/xotem/projects/xotplot/src/xotplot/spec.py): Full configuration for the Projection & Region view.
- [`PlotSpec`](file:///home/xotem/projects/xotplot/src/xotplot/spec.py): Root plot configuration schema supporting file persistence (`to_json_file`, `from_json_file`).

## GUI Integration (`src/xotplot/gui/views/projection_region_view.py`)

- `to_spec() -> RegionViewSpec`: Extracts current UI state into a validated `RegionViewSpec`.
- `apply_spec(spec: RegionViewSpec) -> None`: Populates all UI controls and applies redraw from a validated `RegionViewSpec`.
