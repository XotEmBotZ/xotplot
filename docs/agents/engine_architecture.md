# Plotting Engine Architecture (`xotplot.engine`)

This document records the stateless rendering engine architecture extracted from GUI views.

## Architecture & Responsibilities
- **Stateless & Headless**: The engine does not know or care about PyQt6, GUI widgets, or threads. It takes Pydantic models (`RegionViewSpec`, `PlotSpec`) and renders onto a Matplotlib `Figure`.
- **Single Source of Truth**: All components (PyQt6 views, Textual TUI, CLI batch engine) use the same rendering functions.
- **Fail-Fast & Strict Light Theme**: Plot surfaces strictly use `#ffffff` canvas backgrounds as defined in `src/xotplot/constants.py`.

## Modules
- [`src/xotplot/engine/renderer.py`](file:///home/xotem/projects/xotplot/src/xotplot/engine/renderer.py):
  - `build_crs(proj_spec: ProjectionSpec) -> Any`: Constructs the appropriate Cartopy CRS.
  - `render_region_plot(spec: RegionViewSpec, figure: Optional[Figure] = None) -> Figure`: Renders the base projection, boundaries, features, custom shapefiles, and graticules.
- [`src/xotplot/engine/__init__.py`](file:///home/xotem/projects/xotplot/src/xotplot/engine/__init__.py): Re-exports engine API.

## Consumption in GUI View
In [`src/xotplot/gui/views/projection_region_view.py`](file:///home/xotem/projects/xotplot/src/xotplot/gui/views/projection_region_view.py):
- `apply_projection()` simply calls `render_region_plot(self.to_spec(), figure=self.figure)`.
- No Matplotlib or Cartopy drawing logic remains inside the GUI widget.
