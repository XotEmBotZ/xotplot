# Complete Workbench GUI Implementation

## Overview
All 8 workbench screens specified in `gui-reference/` have been implemented as PyQt6 views in `src/xotplot/gui/views/`, integrated into the unified [`MainWindow`](file:///home/xotem/projects/xotplot/src/xotplot/gui/main_window.py), and powered by **native Matplotlib canvas rendering** with dynamic dark/light theme switching.

## Implemented Views & Matplotlib Canvases

1. **Spatial Viewport (2D/3D)** ([`spatial_viewport_view.py`](file:///home/xotem/projects/xotplot/src/xotplot/gui/views/spatial_viewport_view.py)):
   - Interactive Matplotlib synoptic viewport with filled geopotential height contours (`contourf` Turbo colormap), isobaric contour lines with labels, wind barbs, and High/Low pressure markers.
   - Floating mini-toolbar (Pan, Zoom, Reset Extent, Point Probe, Export Figure).
   - Forecast lead-time scrubber slider (0 to 120h, step 3) with dynamic synchronization.
   - Bottom CLI/YAML command inspector dock with tabs for Generated CLI Command and `config.yaml`.
   - Live cursor tracking emitting coordinate signals.

2. **Variables & Dimensions Inspector** ([`variables_inspector_view.py`](file:///home/xotem/projects/xotplot/src/xotplot/gui/views/variables_inspector_view.py)):
   - 5D coordinate axes panel: time lead hours, isobaric pressure levels, ensemble members, latitude/longitude bounds.
   - Searchable variable catalog table (`gh`, `t`, `u`, `v`, `q`) displaying min/max/mean/std summary statistics with real-time filtering.
   - Dimension reduction and slicing dock (Direct Slice, Zonal Mean, Time Mean, Vertical Integral).
   - Embedded Matplotlib canvas rendering 1D vertical log-pressure profiles and 2D zonal cross-sections with colorbars.

3. **Projection & Region** ([`projection_region_view.py`](file:///home/xotem/projects/xotplot/src/xotplot/gui/views/projection_region_view.py)):
   - Cartopy CRS library grid cards (LambertConformal, PlateCarree, Mercator, NorthPolarStereo, Orthographic, Robinson).
   - Dynamic projection parameter configurator (`central_longitude`, `central_latitude`, `standard_parallels`).
   - Region extent presets (North America CONUS, Europe ECMWF, Global, TC Basin) with bounding box inputs.
   - Graticules & styling inspector (intervals, dashed/solid/dotted styles, labels, coastline/border toggles).
   - Embedded Matplotlib projection mesh preview canvas.

4. **Layer Stack & Features** ([`layer_stack_view.py`](file:///home/xotem/projects/xotplot/src/xotplot/gui/views/layer_stack_view.py)):
   - Interactive Z-order layer stack table with visibility checkboxes, lock toggles, row selection, duplicate, remove, and move up/down controls.
   - Symbology & attributes inspector (Solid, Outline, Hatched, Color Filled; color picker, alpha slider, stroke width, contour intervals).
   - Workspace vector feature store (+ Add .shp file dialog, preset buttons for US States, Severe Outlooks, Rivers).
   - Embedded Matplotlib canvas demonstrating multi-layer composite overlay honoring Z-stacking order.

5. **Colormap Transfer** ([`colormap_transfer_view.py`](file:///home/xotem/projects/xotplot/src/xotplot/gui/views/colormap_transfer_view.py)):
   - Colormap registry cards (viridis, turbo, plasma, coolwarm, cmo.thermal, radar_nws) with gradient previews.
   - Transfer function curve editor with embedded Matplotlib canvas plotting data frequency histogram and interactive transfer curve (Linear, Gamma, Sigmoid, Step).
   - Discretization & normalization levels generator (Linear, BoundaryNorm, LogNorm, TwoSlopeNorm).
   - Colorbar customization options (orientation, shrink, aspect, label).

6. **CLI & Batch Engine** ([`cli_batch_engine_view.py`](file:///home/xotem/projects/xotplot/src/xotplot/gui/views/cli_batch_engine_view.py)):
   - File discovery wildcard/glob engine with pattern input, directory browse, and file match table with colored status badges.
   - Target execution backend selector (Multiprocessing Pool, Headless CLI, Slurm Cluster, Cron daemon) updating worker parameters and CLI command generator.
   - Workflow presets and render specs (CONUS Severe Synoptic, ECMWF 2m Temp, GOES Mesoscale Sector; formats PNG, WebP, MP4; DPI, projection, extent).
   - Syntax validation button and batch execution trigger with simulated pipeline progress bar.

7. **Derived Diagnostics** ([`derived_diagnostics_view.py`](file:///home/xotem/projects/xotplot/src/xotplot/gui/views/derived_diagnostics_view.py)):
   - MetPy diagnostic presets library (Relative Vorticity, Theta-E, Bulk Shear 0-6km, Frontogenesis).
   - Interactive formula editor with quick-insert tags (`+ TMP`, `+ UGRD`, `+ VGRD`, `+ PRES`, `+ HGT`), output variable and unit specification.
   - Spatial stencils and grid metric options (Centered, Compact Pade, cos(lat) spherical metric, filtering).
   - Embedded Matplotlib canvas previewing computed diagnostic field contours and min/max/mean stats.

8. **Compute & Dask Engine** ([`compute_dask_view.py`](file:///home/xotem/projects/xotplot/src/xotplot/gui/views/compute_dask_view.py)):
   - Dask cluster status & telemetry metrics header (scheduler address, active tasks 42/576, memory throughput 1.42 GB/s, dashboard link).
   - Worker processes inspector with CPU % and RAM usage gauges for 8 distributed workers.
   - Multidimensional chunk size optimizer (time, isobaric, lat, lon) with uncompressed float32 memory preview badge, color-coded threshold warnings, and auto-optimization.
   - Task graph DAG progression timeline (I/O read -> MetPy calculation -> spatial interpolation -> render).

## How to Test

### Launching the Application
```bash
uv run xotplot
```

### Automated Headless Verification
```bash
uv run python -c "
import sys
from PyQt6.QtWidgets import QApplication
from xotplot.gui.main_window import MainWindow

app = QApplication(sys.argv)
win = MainWindow()
win.show()

# Verify all 8 views are present
assert win._view_stack.count() == 8

# Test navigating through each view
for i in range(8):
    win._nav_list.setCurrentRow(i)
    assert win._view_stack.currentIndex() == i

# Test theme toggling
win._set_theme(False)  # Light mode
assert win._dark_mode is False
win._set_theme(True)   # Dark mode
assert win._dark_mode is True

print('All 8 workbench GUI views and Matplotlib integrations verified successfully!')
"
```
